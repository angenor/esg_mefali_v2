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

from app.agent.guardrails.lang_check import detect_language, needs_french_retry
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

_FALLBACK_LOOP = (
    "Boucle détectée, opération annulée — peux-tu reformuler ta demande "
    "ou la décomposer en étapes plus simples ?"
)

_FALLBACK_SOURCING = (
    "Je ne dispose pas de source vérifiée pour cette information."
)

_FALLBACK_LANG_FR = (
    "Je rencontre une difficulté à formuler ma réponse en français. "
    "Peux-tu reformuler ta demande ?"
)


def _build_lang_retry_system_message() -> SystemMessage:
    """F58 / US3 — message système forçant la prochaine génération en FR."""
    return SystemMessage(
        content=(
            "Note système (politique de langue) : la réponse précédente "
            "n'était pas en français, alors que la préférence utilisateur "
            "est `fr`. Tu DOIS répondre **en français** uniquement. Pas "
            "d'anglais, d'espagnol ou d'arabe en sortie texte (les "
            "terminologies techniques anglaises courantes — API, ESG, KPI "
            "— restent autorisées). Réponds à nouveau."
        ),
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
    # F58 / US7 — Loop détectée par validate_payload : on stoppe avec un
    # message poli FR (l'erreur est non retriable, le LLM ne peut pas s'en
    # sortir tout seul). Ce check passe AVANT la validation générique car
    # on veut un message dédié plus clair que le fallback validation.
    if any(e.code == "loop_detected" for e in state.errors):
        return {
            "final_text": _FALLBACK_LOOP,
            "sourcing_decision": "accept",
            "loop_detected": True,
        }

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
        # F58 / US3 — Avant de finaliser, on vérifie la langue de la réponse.
        # Si l'utilisateur préfère le français mais le LLM a dérivé vers
        # en/es/ar, on relance UNE FOIS avec une consigne FR. Sinon on
        # garde la réponse telle quelle. La détection est tolérante aux
        # textes courts et au mélange terminologique technique.
        lang_patch = _maybe_request_french_retry(state, text)
        if lang_patch is not None:
            return lang_patch

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


def _maybe_request_french_retry(state: AgentState, text: str) -> dict | None:
    """F58 / US3 — décide si un retry FR doit être déclenché.

    Retourne un patch state à appliquer si retry, sinon None.

    Politique :
    - locale utilisateur ≠ 'fr' → pas de politique FR.
    - texte court (< 30 chars utiles) → ``unknown``, pas de retry (tolérance
      faux positifs).
    - retry déjà consommé (``lang_retry_count >= 1``) → fallback texte FR si
      la réponse reste non-FR ; on log mais on ne ré-essaie pas.
    """
    user_lang = state.context_json.locale
    if user_lang != "fr":
        return None

    detected = detect_language(text)
    if not needs_french_retry(detected, user_lang_pref=user_lang, offer_accepted_langs=None):
        return None

    if state.lang_retry_count >= 1:
        # Retry déjà consommé : on substitue par un fallback FR poli plutôt
        # que d'envoyer du texte non-FR à l'utilisateur (FR-006 strict).
        try:
            logger.warning(
                "lang_retry_exhausted",
                extra={
                    "agent_run_id": str(state.agent_run_id) if state.agent_run_id else None,
                    "detected_lang": detected,
                },
            )
        except Exception:  # pragma: no cover
            pass
        return {
            "final_text": _FALLBACK_LANG_FR,
            "language_corrected": True,
            "sourcing_decision": "fallback",
        }

    # 1er retry : on appose un SystemMessage et on rebascule vers call_llm.
    try:
        logger.info(
            "lang_retry_triggered",
            extra={
                "agent_run_id": str(state.agent_run_id) if state.agent_run_id else None,
                "detected_lang": detected,
            },
        )
    except Exception:  # pragma: no cover
        pass
    return {
        "messages": [_build_lang_retry_system_message()],
        "lang_retry_count": state.lang_retry_count + 1,
        "language_corrected": True,
        # final_text vide ⇒ le router doit rebascule vers call_llm. On
        # réutilise le mécanisme existant de sourcing retry en posant
        # ``sourcing_decision='retry'`` (le router compose_response déjà
        # configuré l'interprète comme « relance LLM »).
        "sourcing_decision": "retry",
        "final_text": "",
    }


__all__ = ["NODE_NAME", "node_compose_response"]
