"""F53 — Repository CRUD pour ``agent_run`` et ``agent_run_step``.

Append-only :
- ``app_user`` peut SELECT + INSERT.
- L'unique ``UPDATE`` (complétion) doit être exécuté via une session avec
  rôle élevé : on ouvre une transaction où ``SET LOCAL ROLE app_admin``
  est positionné, on UPDATE, on RESET ROLE.
- Toujours sous RLS (FR-013) : la session DOIT avoir
  ``app.current_account_id`` positionné avant tout INSERT.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def start_run(
    session: Session,
    *,
    account_id: UUID,
    user_id: UUID,
    thread_id: str,
) -> UUID:
    """Insère un nouveau ``agent_run`` row et retourne son ``id``.

    ``status`` part à ``ok`` par défaut ; sera mis à jour en finalisation.
    """
    row = session.execute(
        text(
            "INSERT INTO agent_run "
            "(account_id, user_id, thread_id, started_at, status, retry_count) "
            "VALUES (:aid, :uid, :tid, :sa, 'ok', 0) "
            "RETURNING id"
        ),
        {
            "aid": account_id,
            "uid": user_id,
            "tid": thread_id,
            "sa": datetime.now(UTC),
        },
    ).fetchone()
    if row is None:  # pragma: no cover - defensive
        raise RuntimeError("agent_run INSERT n'a pas retourné de id")
    return row[0]


def record_step(
    session: Session,
    *,
    run_id: UUID,
    account_id: UUID,
    node_name: str,
    latency_ms: int | None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    tool_calls_count: int = 0,
    status: str = "ok",
    error: str | None = None,
) -> UUID:
    """Insère un row ``agent_run_step`` (append-only).

    Status ∈ {ok, error, timeout, cancelled, skipped}.
    """
    row = session.execute(
        text(
            "INSERT INTO agent_run_step "
            "(run_id, account_id, node_name, latency_ms, tokens_in, tokens_out, "
            " tool_calls_count, status, error) "
            "VALUES (:rid, :aid, :nn, :lat, :ti, :to, :tcc, :st, :err) "
            "RETURNING id"
        ),
        {
            "rid": run_id,
            "aid": account_id,
            "nn": node_name,
            "lat": latency_ms,
            "ti": tokens_in,
            "to": tokens_out,
            "tcc": tool_calls_count,
            "st": status,
            "err": _truncate(error),
        },
    ).fetchone()
    if row is None:  # pragma: no cover - defensive
        raise RuntimeError("agent_run_step INSERT n'a pas retourné de id")
    return row[0]


def complete_run(
    session: Session,
    *,
    run_id: UUID,
    status: str,
    total_latency_ms: int | None = None,
    total_tokens_in: int | None = None,
    total_tokens_out: int | None = None,
    retry_count: int = 0,
    final_node: str | None = None,
    error_summary: str | None = None,
) -> None:
    """UPDATE de complétion ; nécessite ``SET LOCAL ROLE app_admin`` ou rôle migrator.

    Cette exception au strict append-only est documentée dans
    ``backend/alembic/README.md``.
    """
    params: dict[str, Any] = {
        "rid": run_id,
        "ca": datetime.now(UTC),
        "st": status,
        "tl": total_latency_ms,
        "ti": total_tokens_in,
        "to": total_tokens_out,
        "rc": retry_count,
        "fn": final_node,
        "es": _truncate(error_summary, max_len=4000),
    }
    session.execute(
        text(
            "UPDATE agent_run SET "
            "completed_at = :ca, status = :st, total_latency_ms = :tl, "
            "total_tokens_in = :ti, total_tokens_out = :to, "
            "retry_count = :rc, final_node = :fn, error_summary = :es "
            "WHERE id = :rid"
        ),
        params,
    )


def mark_run_cancelled(
    session: Session, *, run_id: UUID, error_summary: str | None = None
) -> None:
    """Raccourci : marque un run comme ``cancelled``."""
    complete_run(
        session,
        run_id=run_id,
        status="cancelled",
        error_summary=error_summary or "client disconnected",
    )


def mark_run_timeout(
    session: Session,
    *,
    run_id: UUID,
    final_node: str | None = None,
) -> None:
    """Raccourci : marque un run comme ``timeout``."""
    complete_run(
        session,
        run_id=run_id,
        status="timeout",
        final_node=final_node,
        error_summary="LLM_AGENT_TIMEOUT_S exceeded",
    )


def get_run(session: Session, *, run_id: UUID) -> dict[str, Any] | None:
    """Lecture (debug/tests) d'un run par id ; retourne dict ou None."""
    row = session.execute(
        text(
            "SELECT id, account_id, user_id, thread_id, started_at, "
            "completed_at, status, total_latency_ms, total_tokens_in, "
            "total_tokens_out, retry_count, final_node, error_summary "
            "FROM agent_run WHERE id = :rid"
        ),
        {"rid": run_id},
    ).mappings().fetchone()
    return dict(row) if row else None


def list_steps(session: Session, *, run_id: UUID) -> list[dict[str, Any]]:
    """Lecture (debug/tests) des steps d'un run."""
    rows = session.execute(
        text(
            "SELECT id, run_id, account_id, node_name, started_at, "
            "latency_ms, tokens_in, tokens_out, tool_calls_count, status, error "
            "FROM agent_run_step WHERE run_id = :rid ORDER BY started_at"
        ),
        {"rid": run_id},
    ).mappings().fetchall()
    return [dict(r) for r in rows]


def _truncate(s: str | None, *, max_len: int = 1000) -> str | None:
    if s is None:
        return None
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


__all__ = [
    "complete_run",
    "get_run",
    "list_steps",
    "mark_run_cancelled",
    "mark_run_timeout",
    "record_step",
    "start_run",
]
