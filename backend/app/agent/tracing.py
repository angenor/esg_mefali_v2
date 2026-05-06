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
from dataclasses import dataclass
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
        async with traced_node(ctx, node_name="route"):
            ... # exécution du nœud

    Si ctx.run_id est None ou ctx.session est None, l'écriture DB est skippée.
    """
    start = time.perf_counter()
    status = "ok"
    error: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    tool_calls_count = 0
    try:
        yield ctx
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
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    tool_calls_count=tool_calls_count,
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
    "TraceContext",
    "get_trace_mode",
    "traced_node",
    "traced_node_sync",
]
