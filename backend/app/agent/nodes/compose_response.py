"""F53 / T036 — Nœud ``compose_response`` : finalise le texte assistant.

Responsabilités :
- assembler ``state.final_text`` à partir de ``state.llm_response_text`` ;
- si ``state.errors`` contient un ``validation_error`` non récupéré,
  retourner un fallback texte sobre FR (US3) ;
- ne PAS persister si la run est cancelled (le runner gère cela en propre).

La persistance assistant (insertion en ``chat_message`` + audit) est
déléguée au runner pour mieux corréler avec le ``thread_id`` chat.
"""

from __future__ import annotations

from app.agent.state import AgentState

NODE_NAME = "compose_response"

_FALLBACK_VALIDATION = (
    "Je n'arrive pas à formaliser cette action — peux-tu reformuler "
    "ta demande différemment ?"
)


def _has_unrecoverable_validation_error(state: AgentState) -> bool:
    """True si l'état contient ≥1 ``validation_error`` non retriable."""
    return any(
        e.code == "validation_error" and not e.retriable
        for e in state.errors
    )


async def node_compose_response(state: AgentState) -> dict:
    """Finalise ``state.final_text``.

    Cas :
    1. ``llm_response_text`` non vide → l'utiliser tel quel (texte du LLM).
    2. Sinon si erreurs validation max atteintes → fallback FR.
    3. Sinon si tool_invoke (SSE_ONLY/DB_MUTATION dispatché) sans texte LLM →
       phrase de courtoisie minimale.
    4. Sinon → texte neutre.
    """
    if _has_unrecoverable_validation_error(state):
        return {"final_text": _FALLBACK_VALIDATION}

    if state.llm_response_text:
        return {"final_text": state.llm_response_text}

    # Si on a fait un dispatch (mutation ou ask), on génère un texte court FR
    if state.dispatch_results:
        # L'UX réelle est portée par la bottom sheet ; on évite de doublonner
        return {"final_text": ""}

    return {"final_text": ""}


__all__ = ["NODE_NAME", "node_compose_response"]
