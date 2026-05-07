"""F53 / T023 — Tracing helper : décorateur ``@traced_node`` + ``traced_run``.

À chaque exécution de nœud :
- mesure ``time.perf_counter()`` ;
- accumule tokens éventuels ;
- écrit un row ``agent_run_step`` via ``app.agent.repository.record_step``.

Mode ``LLM_AGENT_TRACE`` :
- ``off`` : aucun écrit DB ;
- ``db`` : écrit DB uniquement ;
- ``db+stdout`` : écrit DB + structured JSON log.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.repository import record_step
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TraceContext:
    """Contexte de tracing partagé par les nœuds d'un même run."""

    run_id: UUID | None
    account_id: UUID
    session: Session | None
    trace_mode: str = "db"
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_tool_calls: int = 0
    last_node_name: str | None = None


@dataclass
class StepCounters:
    """Compteurs setables par le caller dans le bloc ``async with traced_node``.

    Permettent au wrapper de propager les tokens consommés par le nœud (ex.
    ``call_llm`` lisant ``ai_response.usage_metadata``) vers le step et
    l'agrégat final.
    """

    tokens_in: int | None = None
    tokens_out: int | None = None
    tool_calls_count: int = 0
    extras: dict[str, Any] = field(default_factory=dict)


def _should_write_db(mode: str) -> bool:
    return mode in ("db", "db+stdout")


def _should_log_stdout(mode: str) -> bool:
    return mode == "db+stdout"


@asynccontextmanager
async def traced_node(
    ctx: TraceContext,
    *,
    node_name: str,
):
    """Mesure la latence d'un bloc et écrit un ``agent_run_step``.

    Usage :
        async with traced_node(ctx, node_name="route") as counters:
            result = await node_fn(state)
            counters.tokens_in = ...  # optionnel
            counters.tokens_out = ...
            counters.tool_calls_count = ...

    Si ``ctx.run_id`` est None ou ``ctx.session`` est None, l'écriture DB
    est skippée mais la mesure de latence reste effectuée.
    """
    counters = StepCounters()
    start = time.perf_counter()
    status = "ok"
    error: str | None = None
    try:
        yield counters
    except TimeoutError as exc:
        status = "timeout"
        error = str(exc)
        raise
    except Exception as exc:  # noqa: BLE001
        status = "error"
        error = str(exc)
        raise
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        # Agrégation dans le TraceContext (utilisée par le runner pour
        # complete_run avec total_tokens_in/out).
        if counters.tokens_in:
            ctx.total_tokens_in += int(counters.tokens_in)
        if counters.tokens_out:
            ctx.total_tokens_out += int(counters.tokens_out)
        ctx.total_tool_calls += int(counters.tool_calls_count)
        ctx.last_node_name = node_name
        if (
            ctx.run_id is not None
            and ctx.session is not None
            and _should_write_db(ctx.trace_mode)
        ):
            try:
                record_step(
                    ctx.session,
                    run_id=ctx.run_id,
                    account_id=ctx.account_id,
                    node_name=node_name,
                    latency_ms=latency_ms,
                    tokens_in=counters.tokens_in,
                    tokens_out=counters.tokens_out,
                    tool_calls_count=counters.tool_calls_count,
                    status=status,
                    error=error,
                )
            except Exception:  # pragma: no cover - tracing must never break
                logger.exception("Failed to write agent_run_step")
        if _should_log_stdout(ctx.trace_mode):
            logger.info(
                json.dumps(
                    {
                        "kind": "agent.step",
                        "node": node_name,
                        "latency_ms": latency_ms,
                        "status": status,
                        "error": error,
                        "tokens_in": counters.tokens_in,
                        "tokens_out": counters.tokens_out,
                    }
                )
            )


def traced_node_sync(
    node_name: str,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Décorateur sync (legacy) — préférer ``async with traced_node(ctx, ...)``."""

    def _decorator(
        func: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return _wrapper

    return _decorator


def get_trace_mode() -> str:
    """Retourne le mode de tracing courant (``LLM_AGENT_TRACE``)."""
    return get_settings().LLM_AGENT_TRACE


__all__ = [
    "StepCounters",
    "TraceContext",
    "get_trace_mode",
    "traced_node",
    "traced_node_sync",
]
