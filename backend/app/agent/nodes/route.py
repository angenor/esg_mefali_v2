"""F53 / T029 + F58 / US1+US2 — Nœud ``route`` : classifie + détecte
injection + compte les PII détectées.

Responsabilités :
- F53 — Délègue à ``app.orchestrator.intent_classifier`` (F14).
- F58 — Détecte les patterns d'injection (FR-001) et propage le flag dans le
  state. Le wrapper (FR-002) sera appliqué par le node ``call_llm`` au moment
  de transmettre le message au LLM.
- F58 — Compte les PII (mobile money, IBAN, carte, CNI) présentes dans le
  message utilisateur et propage ``pii_masked_count`` (FR-003). Le LLM voit
  toujours l'original (besoin métier) ; seules les écritures DB ultérieures
  appliquent le masquage.
"""

from __future__ import annotations

from app.agent.guardrails.anti_injection import detect
from app.agent.guardrails.pii_detector import mask_pii
from app.agent.state import AgentState, Intent
from app.orchestrator.intent_classifier import classify

NODE_NAME = "route"


async def node_route(state: AgentState) -> dict:
    """Classifie ``state.user_message``, écrit ``intent``, ``injection_detected``
    et ``pii_masked_count``.

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

    # F58 — PII detection (FR-003). On compte les PII pour les écritures DB ;
    # le user_message envoyé au LLM reste intact (besoin métier).
    _, pii_count = mask_pii(state.user_message)

    return {
        "intent": intent,
        "injection_detected": finding is not None,
        "pii_masked_count": pii_count,
    }


__all__ = ["NODE_NAME", "node_route"]
