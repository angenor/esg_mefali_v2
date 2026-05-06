"""F53 / T032 — Nœud ``select_tools`` : sélectionne ≤ ``LLM_AGENT_MAX_TOOLS``.

F56 (FR-008) : si ``LLM_AGENT_SOURCING_MODE != 'off'``, force la présence
des 3 tools de sourçage (``cite_source``, ``search_source``,
``flag_unsourced``) dans ``state.available_tools`` même si le sélecteur
F14 ne les retourne pas. Ces 3 tools sont ajoutés **au-delà** de la
limite ``LLM_AGENT_MAX_TOOLS`` (le hard cap matériel
``HARD_TOOL_CALLS_CAP=10`` continue de plafonner les invocations).
"""

from __future__ import annotations

from app.agent.state import AgentState, Intent
from app.agent.tool_factory import list_tool_names
from app.config import get_settings

NODE_NAME = "select_tools"

# F56 / FR-008 — Tools forcés à chaque tour quand mode != off.
SOURCING_FORCED_TOOLS: tuple[str, ...] = (
    "cite_source",
    "search_source",
    "flag_unsourced",
)


async def node_select_tools(state: AgentState) -> dict:
    """Renseigne ``state.available_tools`` selon ``state.intent``.

    Si l'intent n'a pas encore été classifié, fallback sur ``autre`` (FR-017).
    Plafonne par ``LLM_AGENT_MAX_TOOLS``.

    F56 : injecte les 3 sourcing tools si ``mode != off``, indépendamment
    du sélecteur F14. Ces tools ne consomment pas de budget sur la limite
    métier (FR-008).
    """
    settings = get_settings()
    intent = state.intent or Intent.AUTRE
    page = state.context_json.page_route
    names = list_tool_names(intent, max_tools=settings.LLM_AGENT_MAX_TOOLS)
    # Note: page is not yet used by the selector; reserved for F54 routing
    _ = page

    # F56 / FR-008 — force sourcing tools (au-delà du cap métier).
    sourcing_mode = getattr(settings, "LLM_AGENT_SOURCING_MODE", "strict")
    if sourcing_mode != "off":
        # Lazy-import pour assurer l'enregistrement dans TOOL_REGISTRY.
        try:
            import app.orchestrator.tools.sourcing  # noqa: F401
        except Exception:  # pragma: no cover - défensif
            pass

        existing = set(names)
        for forced in SOURCING_FORCED_TOOLS:
            if forced not in existing:
                names.append(forced)
                existing.add(forced)

    return {"available_tools": names}


__all__ = ["NODE_NAME", "SOURCING_FORCED_TOOLS", "node_select_tools"]
