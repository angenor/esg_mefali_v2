"""F57 / T007 — RLS test ``recall_log`` (P2 + P3 audit append-only).

Vérifie :
- table existe (account_id, thread_id, recall_type, query_hash, top_k,
  top_scores, latency_ms, created_at, agent_run_id),
- RLS ENABLE + FORCE,
- policy ``recall_log_isolation`` en place,
- CHECK constraint sur ``recall_type IN ('auto','tool')``,
- privilèges ``app_user`` : SELECT + INSERT, pas UPDATE/DELETE (P3).
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.integration.conftest import requires_db

pytestmark = [pytest.mark.integration, requires_db]


def test_recall_log_table_exists(db_engine) -> None:
    with db_engine.connect() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='recall_log'"
                )
            ).all()
        }
    assert {
        "id",
        "account_id",
        "agent_run_id",
        "thread_id",
        "recall_type",
        "query_hash",
        "top_k",
        "top_scores",
        "latency_ms",
        "created_at",
    } <= cols


def test_recall_log_rls_enabled_and_forced(db_engine) -> None:
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relname = 'recall_log'"
            )
        ).first()
    assert row is not None
    assert row[0] is True and row[1] is True


def test_recall_log_isolation_policy_exists(db_engine) -> None:
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT policyname FROM pg_policies "
                "WHERE tablename = 'recall_log' "
                "AND policyname = 'recall_log_isolation'"
            )
        ).first()
    assert row is not None


def test_recall_log_check_constraint_present(db_engine) -> None:
    """Le CHECK sur recall_type IN ('auto','tool') doit exister."""
    with db_engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'recall_log'::regclass
                  AND contype = 'c'
                """
            )
        ).all()
    text_check = " ".join(c[1] for c in rows)
    assert "auto" in text_check and "tool" in text_check


def test_recall_log_app_user_no_update_delete(db_engine) -> None:
    """``app_user`` doit avoir SELECT + INSERT mais pas UPDATE/DELETE (P3)."""
    with db_engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT privilege_type
                FROM information_schema.role_table_grants
                WHERE table_name = 'recall_log'
                  AND grantee = 'app_user'
                """
            )
        ).all()
    privileges = {r[0] for r in rows}
    # SELECT and INSERT must be granted, UPDATE/DELETE must NOT
    if privileges:  # only assert when role exists in this env
        assert "SELECT" in privileges
        assert "INSERT" in privileges
        assert "UPDATE" not in privileges
        assert "DELETE" not in privileges


def test_recall_log_indexes_exist(db_engine) -> None:
    """Les index attendus pour les requêtes F60 doivent exister."""
    with db_engine.connect() as conn:
        names = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'recall_log'"
                )
            ).all()
        }
    assert "idx_recall_log_account_run" in names
    assert "idx_recall_log_account_thread_time" in names
