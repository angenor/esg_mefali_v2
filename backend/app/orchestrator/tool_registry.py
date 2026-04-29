"""Registry de tools auto-descriptifs (US4).

Convention unique : un tool est déclaré une seule fois avec un schéma Pydantic
strict (``extra='forbid'``). Le registre est interrogé par le sélecteur,
le builder de prompt et le validateur — sans duplication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


class UnknownToolError(LookupError):
    """Levée par le validateur si un tool inconnu est invoqué."""


@dataclass(frozen=True)
class ToolDef:
    """Définition immuable d'un tool exposé au LLM."""

    name: str
    description: str
    use_when: str
    dont_use_when: str
    schema: type[BaseModel]
    positive_examples: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    negative_examples: tuple[dict[str, Any], ...] = field(default_factory=tuple)


TOOL_REGISTRY: dict[str, ToolDef] = {}


def tool(
    *,
    name: str,
    description: str,
    use_when: str,
    dont_use_when: str,
    schema: type[BaseModel],
    positive_examples: tuple[dict[str, Any], ...] = (),
    negative_examples: tuple[dict[str, Any], ...] = (),
) -> ToolDef:
    """Enregistre un ``ToolDef`` dans ``TOOL_REGISTRY``.

    Lève ``ValueError`` si le nom est déjà pris (immutabilité du registre)
    ou si le schéma ne déclare pas ``extra='forbid'``.
    """
    if name in TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' déjà enregistré")

    extra = schema.model_config.get("extra") if hasattr(schema, "model_config") else None
    if extra != "forbid":
        raise ValueError(
            f"Tool '{name}' : schéma doit déclarer model_config = ConfigDict(extra='forbid')"
        )

    tool_def = ToolDef(
        name=name,
        description=description,
        use_when=use_when,
        dont_use_when=dont_use_when,
        schema=schema,
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
