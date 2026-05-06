"""F53 / T032 — Nœud ``select_tools`` : sélectionne ≤ ``LLM_AGENT_MAX_TOOLS``.

Délègue à ``app.agent.tool_factory.list_tool_names`` qui consume
``app.orchestrator.tool_selector.select`` (F14). Aucune écriture DB.
"""

from __future__ import annotations

from app.agent.state import AgentState, Intent
from app.agent.tool_factory import list_tool_names
from app.config import get_settings

NODE_NAME = "select_tools"


async def node_select_tools(state: AgentState) -> dict:
    """Renseigne ``state.available_tools`` selon ``state.intent``.

    Si l'intent n'a pas encore été classifié, fallback sur ``autre`` (FR-017).
    Plafonne par ``LLM_AGENT_MAX_TOOLS``.
    """
    settings = get_settings()
    intent = state.intent or Intent.AUTRE
    page = state.context_json.page_route
    names = list_tool_names(intent, max_tools=settings.LLM_AGENT_MAX_TOOLS)
    # Note: page is not yet used by the selector; reserved for F54 routing
    _ = page
    return {"available_tools": names}


__all__ = ["NODE_NAME", "node_select_tools"]
