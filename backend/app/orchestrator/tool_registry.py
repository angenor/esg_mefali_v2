"""Registry de tools auto-descriptifs (US4 / F55).

Convention unique : un tool est déclaré une seule fois avec un schéma Pydantic
strict (``extra='forbid'``). Le registre est interrogé par le sélecteur,
le builder de prompt et le validateur — sans duplication.

F55 ajoute :
- champ ``category: ToolCategory`` (FR-002, fail-fast au boot si manquant) ;
- champ ``requires_confirmation: bool`` pour les mutations destructives (FR-012).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.agent.state import ToolCategory


class UnknownToolError(LookupError):
    """Levée par le validateur si un tool inconnu est invoqué."""


def _infer_category(name: str) -> ToolCategory:
    """Infer une catégorie par défaut depuis le nom du tool.

    Utilisé seulement comme fallback compatibilité ; les nouveaux tools doivent
    déclarer explicitement leur ``category``.
    """
    if name.startswith("ask_"):
        return ToolCategory.ASK
    if name.startswith("show_"):
        return ToolCategory.SHOW
    if name.startswith(
        ("update_", "create_", "delete_", "generate_", "recompute_", "attach_", "revoke_")
    ):
        return ToolCategory.MUTATION
    if name in {"cite_source", "search_source", "recall_history", "flag_unsourced"}:
        return ToolCategory.READ
    # Cas limite : fixtures internes — défaut MUTATION, sans confirmation
    return ToolCategory.MUTATION


@dataclass(frozen=True)
class ToolDef:
    """Définition immuable d'un tool exposé au LLM."""

    name: str
    description: str
    use_when: str
    dont_use_when: str
    schema: type[BaseModel]
    category: ToolCategory = ToolCategory.MUTATION
    requires_confirmation: bool = False
    positive_examples: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    negative_examples: tuple[dict[str, Any], ...] = field(default_factory=tuple)


TOOL_REGISTRY: dict[str, ToolDef] = {}


def tool(  # noqa: PLR0913 — public API
    *,
    name: str,
    description: str,
    use_when: str,
    dont_use_when: str,
    schema: type[BaseModel],
    category: ToolCategory | None = None,
    requires_confirmation: bool = False,
    positive_examples: tuple[dict[str, Any], ...] = (),
    negative_examples: tuple[dict[str, Any], ...] = (),
) -> ToolDef:
    """Enregistre un ``ToolDef`` dans ``TOOL_REGISTRY``.

    Lève ``ValueError`` si le nom est déjà pris (immutabilité du registre)
    ou si le schéma ne déclare pas ``extra='forbid'``.

    Si ``category`` est ``None``, on infère depuis le nom (compat tools
    existants F15/F16/F17). Tout nouveau tool doit déclarer explicitement.
    """
    if name in TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' déjà enregistré")

    extra = schema.model_config.get("extra") if hasattr(schema, "model_config") else None
    if extra != "forbid":
        raise ValueError(
            f"Tool '{name}' : schéma doit déclarer model_config = ConfigDict(extra='forbid')"
        )

    resolved_category = category if category is not None else _infer_category(name)

    tool_def = ToolDef(
        name=name,
        description=description,
        use_when=use_when,
        dont_use_when=dont_use_when,
        schema=schema,
        category=resolved_category,
        requires_confirmation=requires_confirmation,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
    )
    TOOL_REGISTRY[name] = tool_def
    return tool_def


def get_tool(name: str) -> ToolDef:
    """Retourne le ``ToolDef`` enregistré ; lève ``UnknownToolError`` sinon."""
    if name not in TOOL_REGISTRY:
        raise UnknownToolError(f"Tool inconnu : '{name}'")
    return TOOL_REGISTRY[name]


def reset_registry() -> None:
    """Vide le registre (réservé aux tests)."""
    TOOL_REGISTRY.clear()
