"""F53 / T015 — Convertit un ``ToolDef`` (F14 registry) en ``StructuredTool``
LangChain compatible avec ``ChatOpenAI.bind_tools(...)``.

La description LangChain combine ``use_when`` + ``dont_use_when`` pour
guider le LLM (P9 — chaque tool doit dire « use when » / « don't use when »).
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

from app.agent.state import DispatchCategory
from app.orchestrator.schemas import Intent
from app.orchestrator.tool_registry import TOOL_REGISTRY, ToolDef, get_tool
from app.orchestrator.tool_selector import select as select_tool_names


def _build_description(tool_def: ToolDef) -> str:
    """Concatène ``use_when`` + ``dont_use_when`` dans une description LangChain."""
    parts = [tool_def.description.strip()]
    if tool_def.use_when:
        parts.append(f"Use when: {tool_def.use_when.strip()}")
    if tool_def.dont_use_when:
        parts.append(f"Don't use when: {tool_def.dont_use_when.strip()}")
    return "\n\n".join(parts)


def _make_handler(tool_name: str):
    """Handler factice pour un StructuredTool (le dispatch réel est ailleurs).

    LangChain exige une callable, mais le dispatch effectif est délégué au
    nœud ``dispatch_tool`` via le mécanisme tool_calls. Cette fonction est
    donc volontairement un no-op qui retourne le payload validé.
    """

    def _handler(**kwargs: Any) -> dict[str, Any]:
        return {"tool_name": tool_name, "args": dict(kwargs)}

    return _handler


def to_structured_tool(tool_def: ToolDef) -> StructuredTool:
    """Convertit un ``ToolDef`` en ``StructuredTool`` LangChain.

    Le ``args_schema`` est le schéma Pydantic strict (``extra='forbid'``) du
    tool — ce qui force le LLM à n'envoyer que les champs autorisés.
    """
    return StructuredTool.from_function(
        func=_make_handler(tool_def.name),
        name=tool_def.name,
        description=_build_description(tool_def),
        args_schema=tool_def.schema,
    )


# --- Catégorisation tool → DispatchCategory --------------------------------

_REINVOKE_TOOLS = frozenset({"cite_source", "search_source", "recall_history"})
_DB_MUTATION_PREFIXES = ("update_", "create_", "delete_")


def categorize(tool_name: str) -> DispatchCategory:
    """Retourne la catégorie de dispatch d'un tool (FR-007).

    - ``REINVOKE_LLM`` pour ``cite_source`` / ``search_source`` / ``recall_history``
    - ``DB_MUTATION`` pour ``update_*`` / ``create_*`` / ``delete_*``
    - ``SSE_ONLY`` sinon (``ask_*`` / ``show_*``)
    """
    if tool_name in _REINVOKE_TOOLS:
        return DispatchCategory.REINVOKE_LLM
    if tool_name.startswith(_DB_MUTATION_PREFIXES):
        return DispatchCategory.DB_MUTATION
    return DispatchCategory.SSE_ONLY


# --- Sélection bornée par intent --------------------------------------------


def list_active_tools(
    intent: Intent | str,
    *,
    max_tools: int = 10,
    page: str | None = None,
) -> list[StructuredTool]:
    """Retourne la liste des ``StructuredTool`` LangChain pour un ``intent``.

    - Délègue la sélection à ``app.orchestrator.tool_selector.select`` (F14).
    - Plafonne par ``max_tools`` (FR-015 ``LLM_AGENT_MAX_TOOLS``).
    - Ignore silencieusement les noms inconnus du registre.
    """
    intent_value = intent.value if hasattr(intent, "value") else str(intent)
    names = select_tool_names(intent_value, page=page)  # type: ignore[arg-type]
    out: list[StructuredTool] = []
    for name in names[:max_tools]:
        if name not in TOOL_REGISTRY:
            continue
        out.append(to_structured_tool(get_tool(name)))
    return out


def list_tool_names(intent: Intent | str, *, max_tools: int = 10) -> list[str]:
    """Variante string-only de ``list_active_tools`` (utile pour le state)."""
    intent_value = intent.value if hasattr(intent, "value") else str(intent)
    return select_tool_names(intent_value)[:max_tools]  # type: ignore[arg-type]


__all__ = [
    "categorize",
    "list_active_tools",
    "list_tool_names",
    "to_structured_tool",
]
