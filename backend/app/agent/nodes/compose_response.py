"""F53 / T036 — Nœud ``compose_response`` : finalise le texte assistant.

F56 (FR-008..FR-010, FR-016, FR-017) ajoute une étape post-LLM :
1. Récupère ``LLM_AGENT_SOURCING_MODE`` de la config.
2. Appelle ``validate_response`` sur ``llm_response_text`` avec les
   ``validated_calls`` du tour.
3. Selon ``decision`` :
   - ``accept``   → texte final = ``llm_response_text`` ; sources patch.
   - ``retry``    → ToolMessage système expliquant le problème, incrément
     ``sourcing_retry_count`` (max 1), graph rebascule vers ``call_llm``.
   - ``fallback`` → tronquer à la dernière phrase sourcée OU substituer
     "Je ne dispose pas de source vérifiée pour cette information.".
   - ``annotate`` → texte original + (auto unsourced_flag est créé par
     compose_response indirectement — handled by validator helpers).

La persistance assistant (insertion en ``chat_message`` + audit) reste
déléguée au runner (cohérence ``thread_id`` chat).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import SystemMessage

from app.agent.sourcing.models import SourcingValidationResult
from app.agent.sourcing.validator import (
    aggregate_sources_from_calls,
    validate_response,
)
from app.agent.state import AgentState
from app.config import get_settings

logger = logging.getLogger(__name__)

NODE_NAME = "compose_response"

_FALLBACK_VALIDATION = (
    "Je n'arrive pas à formaliser cette action — peux-tu reformuler "
    "ta demande différemment ?"
)

_FALLBACK_SOURCING = (
    "Je ne dispose pas de source vérifiée pour cette information."
)


def _has_unrecoverable_validation_error(state: AgentState) -> bool:
    """True si l'état contient ≥1 ``validation_error`` non retriable."""
    return any(
        e.code == "validation_error" and not e.retriable
        for e in state.errors
    )


def _collect_tool_outputs(state: AgentState) -> list[str]:
    """Concatène le texte sérialisé des résultats READ du tour."""
    outputs: list[str] = []
    for r in state.dispatch_results:
        if r.kind == "tool_message" and r.output:
            content = r.output.get("content")
            if isinstance(content, str):
                outputs.append(content)
    return outputs


def _truncate_to_last_sourced_paragraph(
    text: str, result: SourcingValidationResult
) -> str:
    """Tronque ``text`` à la dernière phrase sourcée, ou substitue le fallback.

    Implementation MVP : si aucune phrase sourcée, retourne le fallback.
    Sinon, retourne le préfixe jusqu'au début du premier claim non sourcé.
    """
    if not result.unsourced_claims:
        return text
    if not result.citations_found:
        return _FALLBACK_SOURCING
    # Tronque au début du 1er claim non sourcé
    first_unsourced = min(c.span[0] for c in result.unsourced_claims)
    truncated = text[:first_unsourced].rstrip(" ,;.\n")
    if not truncated.strip():
        return _FALLBACK_SOURCING
    return truncated + "..."


def _build_retry_system_message(result: SourcingValidationResult) -> SystemMessage:
    """Construit un SystemMessage explicatif pour le retry sourçage."""
    claims_summary = " | ".join(
        f"{c.kind}: '{c.raw}'" for c in result.unsourced_claims[:5]
    )
    content = (
        "Note système (sourçage strict) : la réponse précédente contient "
        "des affirmations factuelles sans citation vérifiée — "
        f"[{claims_summary}]. Pour chaque affirmation factuelle (chiffre, "
        "seuil, formule, mot-clé référentiel), tu DOIS soit (a) appeler "
        "``cite_source(source_id=...)`` avec une source vérifiée — utilise "
        "``search_source`` pour la trouver — soit (b) appeler "
        "``flag_unsourced(claim, reason)`` si aucune source n'existe, soit "
        "(c) reformuler sans cette affirmation. Réponds à nouveau."
    )
    return SystemMessage(content=content)


async def node_compose_response(state: AgentState) -> dict:
    """Finalise ``state.final_text`` + applique la politique de sourcing.

    Cas (par ordre de priorité) :
    1. ``llm_response_text`` vide & erreurs validation → fallback FR.
    2. ``llm_response_text`` non vide → exécute validate_response.
       a. accept    → final = llm_response_text + sources patch.
       b. retry     → re-aiguille vers call_llm (1 retry max).
       c. fallback  → tronque/substitue + sourcing_status=failed.
       d. annotate  → garde le texte (auto unsourced_flag).
    3. dispatch sans texte LLM → vide.
    """
    if _has_unrecoverable_validation_error(state):
        return {"final_text": _FALLBACK_VALIDATION, "sourcing_decision": "accept"}

    settings = get_settings()
    mode = getattr(settings, "LLM_AGENT_SOURCING_MODE", "strict")
    text = state.llm_response_text

    if not text:
        # Cas dispatch sans texte (comportement F53) ou retry où le LLM
        # n'a rien produit. On force ``sourcing_decision='accept'`` pour
        # éviter une boucle infinie sur l'edge graph (FR-019).
        if state.sourcing_retry_count >= 1:
            # Retry consommé sans texte fourni → fallback explicite
            return {
                "final_text": _FALLBACK_SOURCING,
                "sourcing_decision": "fallback",
            }
        if state.dispatch_results:
            return {"final_text": "", "sourcing_decision": "accept"}
        return {"final_text": "", "sourcing_decision": "accept"}

    # Mode 'off' → bypass validator (FR-008)
    if mode == "off":
        return {"final_text": text}

    tool_outputs = _collect_tool_outputs(state)
    result = validate_response(
        text,
        list(state.validated_calls),
        tool_outputs=tool_outputs,
        mode=mode,
        sourcing_retry_count=state.sourcing_retry_count,
    )

    # Log structuré FR-016
    try:
        logger.info(
            "sourcing_check",
            extra={
                "agent_run_id": str(state.agent_run_id) if state.agent_run_id else None,
                "claims_detected": len(result.claims_detected),
                "citations_found": len(result.citations_found),
                "unsourced_count": len(result.unsourced_claims),
                "mode": result.mode,
                "retried": state.sourcing_retry_count > 0,
                "decision": result.decision,
                "duration_ms": result.duration_ms,
            },
        )
    except Exception:  # pragma: no cover
        pass

    patch: dict[str, Any] = {
        "sourcing_decision": result.decision,
    }

    if result.decision == "accept":
        patch["final_text"] = text
        # Aggreger les sources (best-effort — metadata sera enrichi par le runner)
        sources = aggregate_sources_from_calls(list(state.validated_calls))
        if sources:
            patch["chat_message_sources"] = sources
        return patch

    if result.decision == "retry":
        # FR-009 — Append ToolMessage système, incrément retry_count.
        retry_msg = _build_retry_system_message(result)
        patch["messages"] = [retry_msg]
        patch["sourcing_retry_count"] = state.sourcing_retry_count + 1
        # Le graph router (F53) doit voir ce sourcing_decision='retry'
        # pour rebasculer vers call_llm. final_text reste vide pour ne pas
        # finir le tour.
        patch["final_text"] = ""
        return patch

    if result.decision == "fallback":
        # FR-010 — Tronque/substitue + status=failed
        patch["final_text"] = _truncate_to_last_sourced_paragraph(text, result)
        patch["sourcing_decision"] = "fallback"
        return patch

    # decision == "annotate" (mode permissive)
    patch["final_text"] = text
    return patch


__all__ = ["NODE_NAME", "node_compose_response"]
