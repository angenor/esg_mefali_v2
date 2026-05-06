"""F56 / FR-002 — Validator de sourçage (post-LLM, pré ``compose_response``).

API publique :

    validate_response(text, tool_calls, *, tool_outputs=None,
                      mode='strict', sourcing_retry_count=0)
        -> SourcingValidationResult

Algorithme :
1. Découper ``text`` en paragraphes (``\\n\\n``).
2. ``detect_claims(text, tool_outputs=...)`` filtre via la whitelist.
3. Conserver uniquement les claims ``from_tool=False``.
4. Lister les ``cite_source`` dans ``tool_calls`` ; calculer leurs
   ``paragraph_index`` (i-th cite_source couvre du paragraphe i-1 jusqu'à
   l'infini — approximation cumulative R2).
5. Pour chaque claim, déterminer son ``paragraph_index`` ; si aucun
   ``cite_source`` ne couvre ≤ ce paragraphe → claim non sourcé.
6. Décision :
   - mode=off              → accept
   - 0 unsourced           → accept
   - mode=permissive       → annotate
   - mode=strict & retry=0 → retry
   - mode=strict & retry≥1 → fallback

Performance : < 100 ms p95 (NFR-008). Pure-CPU, pas d'I/O.

Logs structurés (FR-016) émis à l'INFO ``sourcing_check`` par le caller
(le validator retourne le résultat ; le logger applicatif est dans
``compose_response``).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from uuid import UUID

from app.agent.sourcing.detector import detect_claims
from app.agent.sourcing.models import (
    CitationRef,
    Claim,
    SourcingDecision,
    SourcingMode,
    SourcingValidationResult,
)
from app.agent.state import ValidatedToolCall

logger = logging.getLogger(__name__)


def _paragraph_offsets(text: str) -> list[tuple[int, int]]:
    """Découpe ``text`` en (start, end) paragraphes (séparateur \\n\\n).

    Garantit ≥1 paragraphe (au minimum le texte entier).
    """
    if not text:
        return [(0, 0)]
    parts: list[tuple[int, int]] = []
    cur = 0
    for raw in text.split("\n\n"):
        end = cur + len(raw)
        parts.append((cur, end))
        cur = end + 2  # +2 pour le séparateur "\n\n"
    if not parts:
        return [(0, len(text))]
    return parts


def _paragraph_index_of(span_start: int, paragraphs: list[tuple[int, int]]) -> int:
    """Retourne l'index 0-based du paragraphe contenant ``span_start``."""
    for i, (s, e) in enumerate(paragraphs):
        if s <= span_start <= e:
            return i
    # Fallback : dernier
    return len(paragraphs) - 1 if paragraphs else 0


def _extract_cite_calls(tool_calls: Iterable[ValidatedToolCall]) -> list[CitationRef]:
    """Extrait les ``cite_source`` valides parmi ``tool_calls``.

    Le ``paragraph_index`` est calculé via l'ordre d'apparition (R2) :
    le i-th cite_source (0-based) couvre du paragraphe i jusqu'à la fin.
    """
    cites = [c for c in tool_calls if c.name == "cite_source"]
    refs: list[CitationRef] = []
    for idx, call in enumerate(cites):
        sid = getattr(call.arguments, "source_id", None)
        if not isinstance(sid, UUID):
            continue
        refs.append(
            CitationRef(
                tool_call_id=call.id,
                source_id=sid,
                paragraph_index=idx,
            )
        )
    return refs


def _paragraph_has_citation(paragraph_idx: int, citations: list[CitationRef]) -> bool:
    """``True`` si une citation couvre ce paragraphe (cumulative).

    Une citation au paragraph_index ``i`` couvre tous les paragraphes ``≥ i``
    (R2 — cumulative MVP).
    """
    if not citations:
        return False
    for c in citations:
        if c.paragraph_index <= paragraph_idx:
            return True
    return False


def validate_response(
    response_text: str,
    tool_calls: list[ValidatedToolCall] | None = None,
    *,
    tool_outputs: list[str] | None = None,
    mode: SourcingMode = "strict",
    sourcing_retry_count: int = 0,
) -> SourcingValidationResult:
    """Valide la réponse contre l'invariant P1.

    Args:
        response_text: Texte assistant final candidat.
        tool_calls: Tous les ``ValidatedToolCall`` du tour (cite_source filtré).
        tool_outputs: Sortie texte des ``ToolMessage`` du tour (READ).
        mode: ``strict`` | ``permissive`` | ``off``.
        sourcing_retry_count: 0 sur première passe ; 1 si retry effectué.

    Returns:
        ``SourcingValidationResult`` avec ``decision`` ∈
        {accept, retry, fallback, annotate}.
    """
    started = time.perf_counter()

    if mode == "off":
        return SourcingValidationResult(
            claims_detected=[],
            citations_found=[],
            unsourced_claims=[],
            mode=mode,
            decision="accept",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    tool_calls = tool_calls or []
    tool_outputs = tool_outputs or []

    raw_claims: list[Claim] = detect_claims(
        response_text, tool_outputs=tool_outputs
    )
    # Exclure les claims provenant d'un tool_output (FR-001)
    claims = [c for c in raw_claims if not c.from_tool]

    citations = _extract_cite_calls(tool_calls)

    paragraphs = _paragraph_offsets(response_text)

    unsourced: list[Claim] = []
    for claim in claims:
        pi = _paragraph_index_of(claim.span[0], paragraphs)
        if not _paragraph_has_citation(pi, citations):
            unsourced.append(claim)

    decision: SourcingDecision
    if not unsourced:
        decision = "accept"
    elif mode == "permissive":
        decision = "annotate"
    elif sourcing_retry_count == 0:
        decision = "retry"
    else:
        decision = "fallback"

    duration_ms = int((time.perf_counter() - started) * 1000)
    return SourcingValidationResult(
        claims_detected=raw_claims,
        citations_found=citations,
        unsourced_claims=unsourced,
        mode=mode,
        decision=decision,
        duration_ms=duration_ms,
    )


def aggregate_sources_from_calls(
    tool_calls: list[ValidatedToolCall],
    cite_metadata: dict[UUID, dict] | None = None,
    *,
    validation_result: SourcingValidationResult | None = None,
) -> list[dict]:
    """FR-011 — Agrège les ``cite_source`` du tour en list de SourceRef-like.

    Sortie volontairement en ``dict`` pour pouvoir être JSON-encodée vers
    ``chat_message.sources`` (JSONB) sans contrainte Pydantic stricte côté
    DB. Le caller (``compose_response``) est libre de wrapper en
    ``SourceRef`` si besoin de validation pré-écriture.

    Args:
        tool_calls: tous les ``ValidatedToolCall`` du tour.
        cite_metadata: optionnel, mapping ``source_id → metadata`` à
            partir des résultats des handlers cite_source. Si absent, le
            caller devra enrichir séparément.
        validation_result: optionnel, contient les ``unsourced_claims``
            pour exclure leurs spans (non utilisé en MVP).

    Returns:
        Liste de dicts ``{source_id, citation_index, ...metadata}``.
    """
    cite_metadata = cite_metadata or {}
    cite_calls = [c for c in tool_calls if c.name == "cite_source"]
    seen: dict[UUID, dict] = {}
    citation_index = 0
    for call in cite_calls:
        sid = getattr(call.arguments, "source_id", None)
        if not isinstance(sid, UUID):
            continue
        if sid in seen:
            continue
        citation_index += 1
        meta = cite_metadata.get(sid, {}) or {}
        entry: dict = {
            "source_id": str(sid),
            "citation_index": citation_index,
            "spans": [],
        }
        # Copy known metadata fields
        for k in (
            "title",
            "publisher",
            "url",
            "page",
            "section",
            "verification_status",
            "version",
        ):
            if k in meta:
                entry[k] = meta[k]
        seen[sid] = entry
    return list(seen.values())


__all__ = [
    "aggregate_sources_from_calls",
    "validate_response",
]
