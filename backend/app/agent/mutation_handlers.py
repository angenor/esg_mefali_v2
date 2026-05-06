"""F55 — Registry des handlers de mutation (FR-007).

Décorateur ``@mutation_handler(tool_name, *, requires_confirmation=False)``
peuple ``MUTATION_HANDLERS`` : un dict ``tool_name → Handler``.

Au boot (``startup_event`` FastAPI), ``ensure_handlers_registered()``
vérifie que :
1. Chaque tool dans ``TOOL_REGISTRY`` a une ``category`` non null ;
2. Chaque tool ``ToolCategory.MUTATION`` a un handler enregistré.

Sinon ``RuntimeError`` (boot fail-fast — FR-008).
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from app.agent.mutation_ctx import MutationCtx
from app.agent.state import MutationResult, ToolCategory
from app.orchestrator.tool_registry import TOOL_REGISTRY

logger = logging.getLogger(__name__)


# Signature du handler :
# async def handler(args: BaseModel, ctx: MutationCtx) -> MutationResult
Handler = Callable[[BaseModel, MutationCtx], Awaitable[MutationResult]]


MUTATION_HANDLERS: dict[str, Handler] = {}


def mutation_handler(
    tool_name: str,
    *,
    requires_confirmation: bool = False,
) -> Callable[[Handler], Handler]:
    """Décorateur : enregistre ``handler`` pour ``tool_name``.

    Si ``requires_confirmation=True``, on patche ``TOOL_REGISTRY[tool_name]``
    pour propager le flag (utilisé par le dispatcher F55 et le frontend ASK).
    """

    def _wrap(handler: Handler) -> Handler:
        if not inspect.iscoroutinefunction(handler):
            raise TypeError(
                f"@mutation_handler('{tool_name}') exige une coroutine async"
            )
        if tool_name in MUTATION_HANDLERS:
            raise ValueError(
                f"Handler déjà enregistré pour tool '{tool_name}'"
            )
        MUTATION_HANDLERS[tool_name] = handler

        # Marquer requires_confirmation sur ToolDef (immuable → on remplace)
        if requires_confirmation and tool_name in TOOL_REGISTRY:
            from dataclasses import replace

            TOOL_REGISTRY[tool_name] = replace(
                TOOL_REGISTRY[tool_name],
                requires_confirmation=True,
            )
        return handler

    return _wrap


def get_handler(tool_name: str) -> Handler | None:
    """Retourne le handler enregistré pour un tool, ou None si absent."""
    return MUTATION_HANDLERS.get(tool_name)


def reset_mutation_handlers() -> None:
    """Vide le registre (réservé aux tests)."""
    MUTATION_HANDLERS.clear()


class HandlerRegistrationError(RuntimeError):
    """Boot fail-fast : un tool MUTATION sans handler ou un tool sans category."""


def ensure_handlers_registered() -> None:
    """Vérifie au boot l'invariant FR-008.

    Lève ``HandlerRegistrationError`` si :
    - un tool MUTATION n'a pas de handler ;
    - un tool n'a pas de category (cas impossible vu ToolDef.category default,
      mais conservé pour défense en profondeur).
    """
    missing_handlers: list[str] = []
    missing_categories: list[str] = []

    for name, tdef in TOOL_REGISTRY.items():
        if tdef.category is None:  # type: ignore[unreachable]
            missing_categories.append(name)
            continue
        if tdef.category == ToolCategory.MUTATION and name not in MUTATION_HANDLERS:
            missing_handlers.append(name)

    if missing_categories:
        raise HandlerRegistrationError(
            f"category missing for: {', '.join(missing_categories)}"
        )
    if missing_handlers:
        raise HandlerRegistrationError(
            f"handler missing for: {', '.join(missing_handlers)}"
        )


def list_registered_handlers() -> dict[str, Any]:
    """Snapshot debug du registre (utilisé par tests + admin endpoint)."""
    return {
        "count": len(MUTATION_HANDLERS),
        "tools": sorted(MUTATION_HANDLERS.keys()),
    }


__all__ = [
    "Handler",
    "HandlerRegistrationError",
    "MUTATION_HANDLERS",
    "ensure_handlers_registered",
    "get_handler",
    "list_registered_handlers",
    "mutation_handler",
    "reset_mutation_handlers",
]
