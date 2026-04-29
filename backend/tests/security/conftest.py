"""T041 — Fixtures pour la suite RLS dédiée."""

from __future__ import annotations

import time
import uuid

import pytest
from sqlalchemy import text

from app.db import get_engine_migrator
from tests.conftest import DB_AVAILABLE

requires_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="Postgres indisponible — démarrer `docker compose up -d postgres`.",
)


@pytest.fixture()
def two_pme():
    """Crée 2 Accounts + 1 entreprise factice par Account via le rôle migrator
    (BYPASS RLS)."""
    eng = get_engine_migrator()
    a1 = uuid.uuid4()
    a2 = uuid.uuid4()
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    suffix = f"{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"

    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (:i, :n, now(), now())"
            ),
            [
                {"i": str(a1), "n": f"acc1_{suffix}"},
                {"i": str(a2), "n": f"acc2_{suffix}"},
            ],
        )
        conn.execute(
            text(
                "INSERT INTO entreprise (id, account_id, name, created_at, updated_at) "
                "VALUES (:i, :a, :n, now(), now())"
            ),
            [
                {"i": str(e1), "a": str(a1), "n": f"E1_{suffix}"},
                {"i": str(e2), "a": str(a2), "n": f"E2_{suffix}"},
            ],
        )

    yield {"account_1": a1, "account_2": a2, "entreprise_1": e1, "entreprise_2": e2}

    # Cleanup
    with eng.begin() as conn:
        conn.execute(text("DELETE FROM entreprise WHERE id IN (:e1, :e2)"), {"e1": str(e1), "e2": str(e2)})
        conn.execute(text("DELETE FROM account WHERE id IN (:a1, :a2)"), {"a1": str(a1), "a2": str(a2)})
