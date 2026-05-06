"""F53 / T012 — Tests d'intégration de la migration Alembic 0032.

Vérifie :
- Les tables ``agent_run`` et ``agent_run_step`` existent.
- RLS active.
- REVOKE UPDATE/DELETE pour ``app_user``.
- CHECK constraint ``agent_run_thread_id_format`` opérationnel.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


def _engine_migrator():
    from app.db import get_engine_migrator

    return get_engine_migrator()


def _engine_app():
    from app.db import engine_app

    return engine_app


@pytest.fixture(autouse=True)
def _require_db():
    try:
        with _engine_migrator().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Postgres indisponible : {exc}")


def test_tables_exist() -> None:
    with _engine_migrator().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name IN ('agent_run', 'agent_run_step') "
                "ORDER BY table_name"
            )
        ).fetchall()
    names = {row[0] for row in rows}
    assert names == {"agent_run", "agent_run_step"}


def test_rls_enabled_on_agent_run() -> None:
    with _engine_migrator().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT relname, relrowsecurity, relforcerowsecurity "
                "FROM pg_class WHERE relname IN ('agent_run', 'agent_run_step') "
                "ORDER BY relname"
            )
        ).fetchall()
    by_name = {row[0]: (row[1], row[2]) for row in rows}
    assert by_name["agent_run"] == (True, True)
    assert by_name["agent_run_step"] == (True, True)


def _seed_account_user(conn) -> tuple:
    """Insère un account + un account_user temporaires et retourne (aid, uid)."""
    account_id = uuid4()
    user_id = uuid4()
    conn.execute(
        text("INSERT INTO account(id, name) VALUES (:id, :name)"),
        {"id": account_id, "name": f"test-acc-{account_id}"},
    )
    conn.execute(
        text(
            "INSERT INTO account_user(id, account_id, email, password_hash, role) "
            "VALUES (:uid, :aid, :email, 'x', 'pme')"
        ),
        {
            "uid": user_id,
            "aid": account_id,
            "email": f"u-{user_id}@x.com",
        },
    )
    return account_id, user_id


def test_thread_id_format_check_constraint_rejects() -> None:
    with _engine_migrator().begin() as conn:
        account_id, user_id = _seed_account_user(conn)
        # Tentative avec thread_id mal formé → CHECK doit lever
        with pytest.raises(Exception) as exc_info:
            conn.execute(
                text(
                    "INSERT INTO agent_run(id, account_id, user_id, thread_id) "
                    "VALUES (:id, :aid, :uid, 'not-uuid:not-uuid')"
                ),
                {"id": uuid4(), "aid": account_id, "uid": user_id},
            )
        # Le message d'erreur Postgres doit citer la contrainte
        msg = str(exc_info.value).lower()
        assert "agent_run_thread_id_format" in msg or "check" in msg


def test_thread_id_format_check_constraint_accepts() -> None:
    with _engine_migrator().begin() as conn:
        account_id, user_id = _seed_account_user(conn)
        thread_id = f"{account_id}:{uuid4()}"
        conn.execute(
            text(
                "INSERT INTO agent_run(id, account_id, user_id, thread_id) "
                "VALUES (:id, :aid, :uid, :tid)"
            ),
            {"id": uuid4(), "aid": account_id, "uid": user_id, "tid": thread_id},
        )


@pytest.mark.parametrize("table", ["agent_run", "agent_run_step"])
def test_app_user_update_delete_revoked(table: str) -> None:
    """app_user ne MUST pas pouvoir UPDATE/DELETE agent_run* (P3 append-only)."""
    with _engine_migrator().connect() as conn:
        privs = conn.execute(
            text(
                "SELECT "
                "  has_table_privilege('app_user', :tbl, 'SELECT')   AS sel, "
                "  has_table_privilege('app_user', :tbl, 'INSERT')   AS ins, "
                "  has_table_privilege('app_user', :tbl, 'UPDATE')   AS upd, "
                "  has_table_privilege('app_user', :tbl, 'DELETE')   AS dele"
            ),
            {"tbl": table},
        ).fetchone()
    assert privs is not None
    sel, ins, upd, dele = privs
    assert sel is True
    assert ins is True
    assert upd is False, f"UPDATE doit être révoqué pour {table}"
    assert dele is False, f"DELETE doit être révoqué pour {table}"
