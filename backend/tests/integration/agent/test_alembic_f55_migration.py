"""F55 / T011 — Test la réversibilité de la migration 0034.

Vérifie que la migration peut être appliquée (upgrade), inversée (downgrade -1)
puis ré-appliquée sans erreur, et que les colonnes/tables apparaissent /
disparaissent correctement.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.conftest import DB_AVAILABLE

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[3]


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    """Run alembic command in backend/ with current env."""
    return subprocess.run(
        ["alembic", *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _has_table(db_engine, table_name: str) -> bool:
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :n"
            ),
            {"n": table_name},
        ).first()
    return row is not None


def _has_column(db_engine, table: str, column: str) -> bool:
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        ).first()
    return row is not None


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_migration_upgrade_creates_table_and_columns(db_engine):
    # On part de l'état head courant (déjà appliqué)
    assert _has_table(db_engine, "tool_call_log")
    assert _has_column(db_engine, "audit_log", "tool_call_id")
    assert _has_column(db_engine, "audit_log", "agent_run_id")


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_migration_reversible(db_engine):
    """Down -1 puis up : structure identique à la fin."""
    # Snapshot avant
    assert _has_table(db_engine, "tool_call_log")

    # Downgrade 1
    res = _run_alembic("downgrade", "-1")
    assert res.returncode == 0, res.stderr

    # Vérifier disparition
    assert not _has_table(db_engine, "tool_call_log")
    assert not _has_column(db_engine, "audit_log", "tool_call_id")
    assert not _has_column(db_engine, "audit_log", "agent_run_id")

    # Re-apply
    res2 = _run_alembic("upgrade", "head")
    assert res2.returncode == 0, res2.stderr
    assert _has_table(db_engine, "tool_call_log")
    assert _has_column(db_engine, "audit_log", "tool_call_id")
    assert _has_column(db_engine, "audit_log", "agent_run_id")


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_idempotency_unique_per_account(db_engine):
    """Le UNIQUE INDEX partial empêche deux lignes même clé pour même account."""
    from uuid import uuid4

    with db_engine.connect() as c:
        with c.begin():
            # Bootstrap account
            acc_id = c.execute(
                text(
                    "INSERT INTO account (id, name, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), 'Idem', now(), now()) RETURNING id"
                )
            ).scalar_one()
            usr_id = c.execute(
                text(
                    "INSERT INTO account_user (id, account_id, email, password_hash, "
                    "role, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) "
                    "RETURNING id"
                ),
                {"a": acc_id, "e": f"idem_unique_{uuid4()}@x.com"},
            ).scalar_one()
            c.execute(
                text("SET LOCAL \"app.current_account_id\" = '" + str(acc_id) + "'")
            )
            c.execute(
                text("SET LOCAL \"app.current_user_id\" = '" + str(usr_id) + "'")
            )
            ikey = "abcd1234" * 4  # 32 chars
            c.execute(
                text(
                    "INSERT INTO tool_call_log "
                    "(id, account_id, user_id, tool_call_id, tool_name, status, "
                    " idempotency_key, created_at, updated_at, version) "
                    "VALUES (gen_random_uuid(), :a, :u, 't1', 'update_x', 'ok', "
                    " :k, now(), now(), 1)"
                ),
                {"a": acc_id, "u": usr_id, "k": ikey},
            )
            from sqlalchemy.exc import IntegrityError

            try:
                c.execute(
                    text(
                        "INSERT INTO tool_call_log "
                        "(id, account_id, user_id, tool_call_id, tool_name, status, "
                        " idempotency_key, created_at, updated_at, version) "
                        "VALUES (gen_random_uuid(), :a, :u, 't2', 'update_x', 'ok', "
                        " :k, now(), now(), 1)"
                    ),
                    {"a": acc_id, "u": usr_id, "k": ikey},
                )
                duplicate_allowed = True
            except IntegrityError:
                duplicate_allowed = False
            assert duplicate_allowed is False
