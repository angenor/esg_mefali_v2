"""F04 — ``@journal_llm_mutation`` decorator (US2).

Wraps an async LLM tool handler so that every successful mutation is journaled
with ``source_of_change='llm'``. F17 (LLM mutations) is the primary consumer.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange


def _extract_entity_id(result: Any) -> UUID | str | None:
    """Best-effort extraction of an entity id from a tool's return value.

    Supports:
    - Pydantic-like models with an ``id`` attribute.
    - Dicts with an ``id`` / ``entity_id`` key.
    - Raw UUID / str values.
    """
    if result is None:
        return None
    if isinstance(result, (UUID, str)):
        return result
    eid = getattr(result, "id", None)
    if eid is not None:
        return eid
    if isinstance(result, dict):
        return result.get("id") or result.get("entity_id")
    return None


def _find_session(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Session | None:
    """Locate a SQLAlchemy session in the call signature."""
    sess = kwargs.get("db") or kwargs.get("session")
    if sess is not None:
        return sess
    for a in args:
        if isinstance(a, Session):
            return a
    return None


def journal_llm_mutation(
    entity_type: str,
    *,
    field: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator factory: wraps a tool to journal its mutation.

    Args:
        entity_type: logical entity name written to ``audit_log.entity_type``.
        field: optional field name when the mutation targets a single column.

    Usage::

        @journal_llm_mutation("projet", field="nom")
        async def update_projet_name(db, projet_id, new_name): ...
    """

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        is_coro = inspect.iscoroutinefunction(fn)

        if is_coro:

            @wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = await fn(*args, **kwargs)
                _emit(args, kwargs, result, entity_type, field)
                return result

            return async_wrapper

        @wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            _emit(args, kwargs, result, entity_type, field)
            return result

        return sync_wrapper

    return decorate


def _emit(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: Any,
    entity_type: str,
    field: str | None,
) -> None:
    db = _find_session(args, kwargs)
    if db is None:
        # No session available — silently skip; F17 is responsible for wiring.
        return
    eid = _extract_entity_id(result)
    if eid is None:
        return
    record_audit(
        db,
        entity_type=entity_type,
        entity_id=eid,
        field=field,
        old=kwargs.get("_old"),
        new=kwargs.get("_new"),
        source_of_change=SourceOfChange.LLM,
        user_id=kwargs.get("_user_id"),
        account_id=kwargs.get("_account_id"),
        request_id=kwargs.get("_request_id"),
    )
