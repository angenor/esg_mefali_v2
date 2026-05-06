"""F53 / T029 — Nœud ``route`` : classifie l'intention de l'utilisateur.

Délègue à ``app.orchestrator.intent_classifier`` (F14). Aucune écriture DB.
"""

from __future__ import annotations

from app.agent.state import AgentState, Intent
from app.orchestrator.intent_classifier import classify

NODE_NAME = "route"


async def node_route(state: AgentState) -> dict:
    """Classifie ``state.user_message`` et écrit ``state.intent``.

    Branchement conditionnel (FR-004) :
    - ``profilage``, ``mutation``, ``analyse`` → contexte complet
    - ``aide``, ``navigation``, ``autre`` → contexte minimal
    - ``question_fermee`` → forçage tool ``ask_*`` (sélection de tools spéciale)
    """
    intent_str = classify(state.user_message, thread_id=state.thread_id)
    intent = Intent(intent_str)
    return {"intent": intent}


__all__ = ["NODE_NAME", "node_route"]
