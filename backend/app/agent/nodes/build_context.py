"""F53 / T030 — Nœud ``build_context`` : construit le contexte LLM.

MVP F53 : version minimale qui injecte ``user_message`` + ``context_json``
+ ID PME comme ``HumanMessage`` LangChain dans ``state.messages``.

F54 polishera ensuite avec :
- profil entreprise injecté
- 3 derniers projets actifs
- system prompt dynamique
- distinction ctx_full vs ctx_min selon ``state.intent``
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import AgentState, Intent

NODE_NAME = "build_context"

_DEFAULT_SYSTEM_PROMPT = (
    "Tu es ESG Mefali, l'assistant IA pour PME ouest-africaines en finance "
    "verte. Tu réponds en français, tu cites tes sources via cite_source pour "
    "tout chiffre ESG ou financier, tu utilises les tools fournis pour les "
    "actions structurées (questions, créations, mises à jour, visualisations)."
)

_FULL_CONTEXT_INTENTS = frozenset({Intent.PROFILAGE, Intent.MUTATION, Intent.ANALYSE})


async def node_build_context(state: AgentState) -> dict:
    """Construit le contexte LLM minimal F53.

    En F53 on alimente :
    - ``messages`` avec un SystemMessage (system_prompt par défaut)
    - puis un HumanMessage (user_message)
    - ``available_tools`` reste vide pour le moment (rempli par select_tools)
    """
    system_prompt = state.system_prompt or _DEFAULT_SYSTEM_PROMPT

    new_messages = []
    # Si le state n'a pas encore de SystemMessage, on l'ajoute
    has_system = any(isinstance(m, SystemMessage) for m in state.messages)
    if not has_system:
        new_messages.append(SystemMessage(content=system_prompt))

    # Toujours ajouter le user message courant
    new_messages.append(HumanMessage(content=state.user_message))

    return {"messages": new_messages}


def is_full_context(intent: Intent | None) -> bool:
    """Indique si l'intent demande un contexte complet (F54-ready)."""
    return intent in _FULL_CONTEXT_INTENTS


__all__ = ["NODE_NAME", "is_full_context", "node_build_context"]
