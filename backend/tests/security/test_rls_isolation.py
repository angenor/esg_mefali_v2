"""T042 — Suite RLS dédiée (≥ 7 cas).

Vérifie que la Row-Level Security PostgreSQL isole strictement les comptes :
- SELECT cross-account → 0 ligne
- LIST → uniquement own
- UPDATE cross-account → 0 ligne affectée
- DELETE cross-account → 0 ligne affectée
- requête sans SET LOCAL → 0 ligne
- INSERT avec mismatch account_id → erreur RLS
- Admin (app.is_admin=true) voit tout
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db import engine_app
from tests.security.conftest import requires_db


def _set_ctx(conn, account_id: uuid.UUID | None, is_admin: bool = False) -> None:
    if account_id:
        conn.execute(text(f"SET LOCAL app.current_account_id = '{account_id}'"))
    conn.execute(text(f"SET LOCAL app.is_admin = '{'true' if is_admin else 'false'}'"))


@requires_db
class TestRlsIsolation:
    def test_select_cross_account_returns_zero(self, two_pme):
        with engine_app.begin() as conn:
            _set_ctx(conn, two_pme["account_1"])
            res = conn.execute(
                text("SELECT count(*) FROM entreprise WHERE id = :i"),
                {"i": str(two_pme["entreprise_2"])},
            ).scalar()
        assert res == 0

    def test_list_returns_only_own(self, two_pme):
        with engine_app.begin() as conn:
            _set_ctx(conn, two_pme["account_1"])
            ids = [str(r[0]) for r in conn.execute(text("SELECT id FROM entreprise")).fetchall()]
        assert str(two_pme["entreprise_1"]) in ids
        assert str(two_pme["entreprise_2"]) not in ids

    def test_update_cross_account_zero_rows(self, two_pme):
        with engine_app.begin() as conn:
            _set_ctx(conn, two_pme["account_1"])
            res = conn.execute(
                text("UPDATE entreprise SET name = 'pwned' WHERE id = :i"),
                {"i": str(two_pme["entreprise_2"])},
            )
        assert res.rowcount == 0

    def test_delete_cross_account_zero_rows(self, two_pme):
        with engine_app.begin() as conn:
            _set_ctx(conn, two_pme["account_1"])
            res = conn.execute(
                text("DELETE FROM entreprise WHERE id = :i"),
                {"i": str(two_pme["entreprise_2"])},
            )
        assert res.rowcount == 0

    def test_query_without_context_zero_rows(self, two_pme):
        with engine_app.begin() as conn:
            # Pas de SET LOCAL : current_account_id est ''
            conn.execute(text("SET LOCAL app.is_admin = 'false'"))
            res = conn.execute(text("SELECT count(*) FROM entreprise")).scalar()
        assert res == 0

    def test_insert_with_mismatch_account_raises(self, two_pme):
        from sqlalchemy.exc import ProgrammingError

        with pytest.raises(ProgrammingError):
            with engine_app.begin() as conn:
                _set_ctx(conn, two_pme["account_1"])
                # tente d'insérer une ligne pour account_2
                conn.execute(
                    text(
                        "INSERT INTO entreprise (id, account_id, name, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :a, 'evil', now(), now())"
                    ),
                    {"a": str(two_pme["account_2"])},
                )

    def test_admin_sees_all(self, two_pme):
        with engine_app.begin() as conn:
            _set_ctx(conn, account_id=None, is_admin=True)
            res = conn.execute(
                text("SELECT count(*) FROM entreprise WHERE id IN (:e1, :e2)"),
                {"e1": str(two_pme["entreprise_1"]), "e2": str(two_pme["entreprise_2"])},
            ).scalar()
        assert res == 2
