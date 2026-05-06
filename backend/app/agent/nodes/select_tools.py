"""F53 / T032 + F56 + F58 — Nœud ``select_tools`` : sélectionne ≤ ``LLM_AGENT_MAX_TOOLS``.

F56 (FR-008) : si ``LLM_AGENT_SOURCING_MODE != 'off'``, force la présence
des 3 tools de sourçage (``cite_source``, ``search_source``,
``flag_unsourced``) dans ``state.available_tools`` même si le sélecteur
F14 ne les retourne pas.

F58 (FR-007/FR-009) : exclut les tools désactivés par admin (``agent_tool_status``).
F58 (FR-025) : en mode ``minimal``, ne garde que ``cite_source`` +
``flag_unsourced`` (texte sourcé seulement).
"""

from __future__ import annotations

import logging

from app.agent.state import AgentState, Intent
from app.agent.tool_factory import list_tool_names
from app.config import get_settings
from app.db import SessionLocal

logger = logging.getLogger(__name__)

NODE_NAME = "select_tools"

# F56 / FR-008 — Tools forcés à chaque tour quand mode != off.
SOURCING_FORCED_TOOLS: tuple[str, ...] = (
    "cite_source",
    "search_source",
    "flag_unsourced",
)

# F58 / FR-025 — Tools autorisés en mode minimal (texte sourcé seulement).
MINIMAL_MODE_TOOLS: frozenset[str] = frozenset({"cite_source", "flag_unsourced"})


async def node_select_tools(state: AgentState) -> dict:
    """Renseigne ``state.available_tools`` selon ``state.intent``.

    Si l'intent n'a pas encore été classifié, fallback sur ``autre`` (FR-017).
    Plafonne par ``LLM_AGENT_MAX_TOOLS``.

    F56 : injecte les 3 sourcing tools si ``mode != off``, indépendamment
    du sélecteur F14.

    F58 : (a) en mode ``minimal``, restreint à ``cite_source`` + ``flag_unsourced``
    uniquement ; (b) exclut les tools désactivés par l'admin via
    ``agent_tool_status`` (cache TTL 30 s).
    """
    settings = get_settings()
    intent = state.intent or Intent.AUTRE
    page = state.context_json.page_route
    names = list_tool_names(intent, max_tools=settings.LLM_AGENT_MAX_TOOLS)
    _ = page  # reserved

    # F58 — Mode minimal : restreint immédiatement (FR-025).
    if settings.LLM_AGENT_MODE == "minimal":
        # Forcer le chargement du registry sourcing (lazy, F56).
        try:
            import app.orchestrator.tools.sourcing  # noqa: F401
        except Exception:  # pragma: no cover
            pass
        # Filtre strict : on ne garde que les tools autorisés en minimal.
        names = [n for n in names if n in MINIMAL_MODE_TOOLS]
        # On ajoute ceux qui manquent
        for required in MINIMAL_MODE_TOOLS:
            if required not in names:
                names.append(required)
        return {"available_tools": names}

    # F56 / FR-008 — force sourcing tools (au-delà du cap métier).
    sourcing_mode = getattr(settings, "LLM_AGENT_SOURCING_MODE", "strict")
    if sourcing_mode != "off":
        try:
            import app.orchestrator.tools.sourcing  # noqa: F401
        except Exception:  # pragma: no cover
            pass

        existing = set(names)
        for forced in SOURCING_FORCED_TOOLS:
            if forced not in existing:
                names.append(forced)
                existing.add(forced)

    # F58 / FR-007 — Exclure les tools désactivés admin (sauf si requestor admin).
    # NB : on ne filtre PAS pour un admin (cf. FR-009). En MVP on ne distingue
    # pas via state ; le comportement par défaut filtre tous (admin compris).
    # L'admin gère ses propres outils via les endpoints admin directement.
    try:
        from app.agent.guardrails.tool_status import get_disabled_tools

        with SessionLocal() as sess:
            disabled = get_disabled_tools(sess)
        if disabled:
            names = [n for n in names if n not in disabled]
    except Exception:  # noqa: BLE001
        logger.debug("get_disabled_tools failed; proceeding without filter", exc_info=True)

    return {"available_tools": names}


__all__ = [
    "MINIMAL_MODE_TOOLS",
    "NODE_NAME",
    "SOURCING_FORCED_TOOLS",
    "node_select_tools",
]
