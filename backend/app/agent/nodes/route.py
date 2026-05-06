"""F53 / T029 + F58 / US1 — Nœud ``route`` : classifie + détecte injection.

Responsabilités :
- F53 — Délègue à ``app.orchestrator.intent_classifier`` (F14).
- F58 — Détecte les patterns d'injection (FR-001) et propage le flag dans le
  state. Le wrapper (FR-002) sera appliqué par le node ``call_llm`` au moment
  de transmettre le message au LLM.
"""

from __future__ import annotations

from app.agent.guardrails.anti_injection import detect
from app.agent.state import AgentState, Intent
from app.orchestrator.intent_classifier import classify

NODE_NAME = "route"


async def node_route(state: AgentState) -> dict:
    """Classifie ``state.user_message``, écrit ``intent`` et flag injection.

    Branchement conditionnel (FR-004) :
    - ``profilage``, ``mutation``, ``analyse`` → contexte complet
    - ``aide``, ``navigation``, ``autre`` → contexte minimal
    - ``question_fermee`` → forçage tool ``ask_*`` (sélection de tools spéciale)
    """
    intent_str = classify(state.user_message, thread_id=state.thread_id)
    intent = Intent(intent_str)

    # F58 — Anti-injection detect (FR-001). On NE bloque PAS le flux : on flag
    # uniquement, et le node call_llm appliquera ``wrap_user_message`` au moment
    # de l'envoi au modèle.
    finding = detect(state.user_message)
    return {
        "intent": intent,
        "injection_detected": finding is not None,
    }


__all__ = ["NODE_NAME", "node_route"]
