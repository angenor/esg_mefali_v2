"""F03 US3 — Middleware ``validate_llm_output``.

Garde finale qui rejette toute sortie LLM contenant un chiffre ESG sans tool-call
``cite_source`` valide vers une source ``verified``.

Politique :
- Heuristiques détectent au moins une affirmation ESG -> exige >= 1 tool_call cite_source.
- Chaque cite_source vérifié via DB (verification_status = 'verified').
- Retry plafonné à 2 ; au-delà : message d'échappatoire neutre.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.llm_validation import decision_cache, heuristics

ReasonCode = Literal[
    "ok",
    "no_citation",
    "source_not_verified",
    "source_not_found",
    "heuristic_match_no_tool",
]

MAX_RETRIES = 2
ESCAPE_HATCH_MESSAGE = (
    "Je ne dispose pas de source vérifiée pour cette donnée. "
    "Je préfère ne pas répondre plutôt que de risquer une information inexacte."
)


@dataclass(frozen=True)
class LLMValidationDecision:
    accepted: bool
    reason_code: ReasonCode | None
    cited_source_ids: tuple[str, ...]
    detected_units: tuple[str, ...]


def _extract_tool_calls(message_json: dict[str, Any]) -> list[dict[str, Any]]:
    return message_json.get("tool_calls") or []


def _extract_cited_source_ids(message_json: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for tc in _extract_tool_calls(message_json):
        if tc.get("type") != "function":
            continue
        fn = tc.get("function") or {}
        if fn.get("name") != "cite_source":
            continue
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            continue
        sid = args.get("source_id")
        if sid:
            ids.append(str(sid))
    return ids


def _verify_sources(
    db: Session, source_ids: list[str]
) -> tuple[bool, ReasonCode | None, int]:
    """Vérifie que toutes les sources existent et sont verified.

    Retourne (ok, reason_code, max_status_version).
    """
    if not source_ids:
        return False, "no_citation", 0
    # Cast UUID
    try:
        ids = [str(uuid.UUID(s)) for s in source_ids]
    except (ValueError, AttributeError):
        return False, "source_not_found", 0
    # On évite le cast :ids::uuid[] (mal supporté par psycopg/SQLAlchemy text())
    # en construisant une clause IN dynamique.
    placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
    params = {f"id_{i}": ids[i] for i in range(len(ids))}
    rows = db.execute(
        text(
            f"SELECT id::text, verification_status, status_version "
            f"FROM source WHERE id IN ({placeholders})"
        ),
        params,
    ).all()
    found = {r[0]: (r[1], r[2]) for r in rows}
    if len(found) < len(set(ids)):
        return False, "source_not_found", 0
    for sid in ids:
        status_, _sv = found[sid]
        if status_ != "verified":
            return False, "source_not_verified", 0
    max_sv = max(sv for _, sv in found.values())
    return True, "ok", int(max_sv)


def validate_llm_output(
    db: Session,
    message_json: dict[str, Any],
) -> LLMValidationDecision:
    """Décide si la sortie LLM peut être servie.

    ``message_json`` est le format OpenAI ``message`` (``content`` + ``tool_calls``).
    """
    content = (message_json.get("content") or "").strip()
    detection = heuristics.detect_esg_claims(content)
    cited = _extract_cited_source_ids(message_json)

    # Pas de chiffre/keyword ESG : autorisé sans cite_source.
    if not detection.has_esg_claim:
        return LLMValidationDecision(
            accepted=True,
            reason_code="ok",
            cited_source_ids=tuple(cited),
            detected_units=detection.detected_units,
        )

    # Chiffre/keyword ESG mais aucun cite_source : refus.
    if not cited:
        return LLMValidationDecision(
            accepted=False,
            reason_code="heuristic_match_no_tool",
            cited_source_ids=(),
            detected_units=detection.detected_units,
        )

    # Cache lookup
    cache_key_pre = decision_cache.make_key(
        message=content, cited_ids=cited, max_status_version=0
    )
    cached = decision_cache.get(cache_key_pre)
    if cached is not None:
        return cached

    # Vérif DB
    ok, reason, max_sv = _verify_sources(db, cited)
    decision = LLMValidationDecision(
        accepted=ok,
        reason_code=reason,
        cited_source_ids=tuple(cited),
        detected_units=detection.detected_units,
    )
    # Recompose la clé avec la vraie max_status_version pour invalidation propre
    cache_key = decision_cache.make_key(
        message=content, cited_ids=cited, max_status_version=max_sv
    )
    decision_cache.put(cache_key, decision)
    decision_cache.put(cache_key_pre, decision)
    return decision


def apply_to_llm_response(
    db: Session,
    *,
    llm_call,
    initial_message: dict[str, Any],
    max_retries: int = MAX_RETRIES,
) -> tuple[dict[str, Any], LLMValidationDecision]:
    """Boucle retry : appelle ``llm_call()`` jusqu'à acceptation ou ``max_retries``.

    ``llm_call`` doit être une callable sans argument retournant un nouveau
    ``message_json``. Au-delà de ``max_retries`` un message d'échappatoire neutre
    est servi.
    """
    msg = initial_message
    decision = validate_llm_output(db, msg)
    attempts = 0
    while not decision.accepted and attempts < max_retries:
        attempts += 1
        msg = llm_call()
        decision = validate_llm_output(db, msg)
    if not decision.accepted:
        return (
            {"role": "assistant", "content": ESCAPE_HATCH_MESSAGE, "tool_calls": []},
            decision,
        )
    return msg, decision
