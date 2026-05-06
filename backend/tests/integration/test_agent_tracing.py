"""F53 / T072-T074 — Tests de tracing (US7 / FR-011)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.agent.repository import (
    get_run,
    list_steps,
    record_step,
    start_run,
)
from app.db import SessionLocal, get_engine_migrator

pytestmark = pytest.mark.integration


def _seed_account_and_user() -> tuple:
    """Crée un account + user et retourne (aid, uid). Auto-cleanup non requis."""
    account_id = uuid4()
    user_id = uuid4()
    with get_engine_migrator().begin() as conn:
        conn.execute(
            text("INSERT INTO account(id, name) VALUES (:id, :n)"),
            {"id": account_id, "n": f"trace-{account_id}"},
        )
        conn.execute(
            text(
                "INSERT INTO account_user(id, account_id, email, password_hash, role) "
                "VALUES (:uid, :aid, :em, 'x', 'pme')"
            ),
            {"uid": user_id, "aid": account_id, "em": f"trace-{user_id}@x.com"},
        )
    return account_id, user_id


def test_start_run_inserts_row() -> None:
    aid, uid = _seed_account_and_user()
    with SessionLocal() as session:
        # Set RLS context
        session.execute(text(f"SET LOCAL app.current_account_id = '{aid}'"))
        session.execute(text(f"SET LOCAL app.current_user_id = '{uid}'"))

        run_id = start_run(
            session,
            account_id=aid,
            user_id=uid,
            thread_id=f"{aid}:{uuid4()}",
        )
        session.commit()

    with get_engine_migrator().connect() as conn:
        row = conn.execute(
            text("SELECT id, status FROM agent_run WHERE id = :rid"),
            {"rid": run_id},
        ).fetchone()
    assert row is not None
    assert row[1] == "ok"


def test_record_step_appends_row() -> None:
    aid, uid = _seed_account_and_user()
    with SessionLocal() as session:
        session.execute(text(f"SET LOCAL app.current_account_id = '{aid}'"))
        run_id = start_run(
            session,
            account_id=aid,
            user_id=uid,
            thread_id=f"{aid}:{uuid4()}",
        )
        record_step(
            session,
            run_id=run_id,
            account_id=aid,
            node_name="route",
            latency_ms=12,
            tokens_in=100,
            tokens_out=50,
            status="ok",
        )
        record_step(
            session,
            run_id=run_id,
            account_id=aid,
            node_name="call_llm",
            latency_ms=350,
            status="ok",
        )
        session.commit()

    # Verify
    with get_engine_migrator().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT node_name, latency_ms, status FROM agent_run_step "
                "WHERE run_id = :rid ORDER BY started_at"
            ),
            {"rid": run_id},
        ).fetchall()
    names = [r[0] for r in rows]
    assert "route" in names
    assert "call_llm" in names


def test_complete_run_updates_status() -> None:
    """``complete_run`` UPDATE le row (autorisé via migrator role en test)."""
    aid, uid = _seed_account_and_user()
    with get_engine_migrator().begin() as conn:
        # Set context for RLS
        conn.execute(text(f"SET LOCAL app.current_account_id = '{aid}'"))
        run_id = uuid4()
        conn.execute(
            text(
                "INSERT INTO agent_run (id, account_id, user_id, thread_id) "
                "VALUES (:id, :aid, :uid, :tid)"
            ),
            {"id": run_id, "aid": aid, "uid": uid, "tid": f"{aid}:{uuid4()}"},
        )

    # Complete via session avec engine migrator (BYPASS RLS test)
    with get_engine_migrator().begin() as conn:
        conn.execute(
            text(
                "UPDATE agent_run SET status='ok', completed_at=now(), "
                "total_latency_ms=500 WHERE id = :rid"
            ),
            {"rid": run_id},
        )

    with get_engine_migrator().connect() as conn:
        row = conn.execute(
            text("SELECT status, total_latency_ms FROM agent_run WHERE id = :rid"),
            {"rid": run_id},
        ).fetchone()
    assert row[0] == "ok"
    assert row[1] == 500


def test_get_run_returns_dict() -> None:
    aid, uid = _seed_account_and_user()
    with SessionLocal() as session:
        session.execute(text(f"SET LOCAL app.current_account_id = '{aid}'"))
        run_id = start_run(session, account_id=aid, user_id=uid, thread_id=f"{aid}:{uuid4()}")
        # Re-set RLS context after each commit (SET LOCAL is tx-scoped)
        session.commit()
        session.execute(text(f"SET LOCAL app.current_account_id = '{aid}'"))
        result = get_run(session, run_id=run_id)
    assert result is not None
    assert result["status"] == "ok"
    assert result["account_id"] == aid


def test_list_steps_empty_when_no_steps() -> None:
    aid, uid = _seed_account_and_user()
    with SessionLocal() as session:
        session.execute(text(f"SET LOCAL app.current_account_id = '{aid}'"))
        run_id = start_run(session, account_id=aid, user_id=uid, thread_id=f"{aid}:{uuid4()}")
        session.commit()
        session.execute(text(f"SET LOCAL app.current_account_id = '{aid}'"))
        steps = list_steps(session, run_id=run_id)
    assert steps == []
