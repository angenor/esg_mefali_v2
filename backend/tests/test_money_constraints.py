"""Tests CHECK Money (T041-T043)."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.conftest import requires_db

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def _ensure_migrations_applied():
    res = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        pytest.skip(f"alembic upgrade head failed: {res.stderr}")
    yield


@pytest.fixture()
def account_id(db_engine):
    """Crée un account éphémère et le rend disponible pour les inserts."""
    aid = str(uuid.uuid4())
    with db_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO account (id, name) VALUES (:id, :n)"),
            {"id": aid, "n": "Test Account Money"},
        )
    yield aid
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM entreprise WHERE account_id=:a"), {"a": aid})
        conn.execute(text("DELETE FROM account WHERE id=:a"), {"a": aid})


@requires_db
def test_amount_without_currency_rejected(db_engine, account_id):
    """T041 — taille_ca_amount sans currency → IntegrityError."""
    with db_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO entreprise (id, account_id, name, taille_ca_amount) "
                    "VALUES (:id, :a, :n, 1000.00)"
                ),
                {"id": str(uuid.uuid4()), "a": account_id, "n": "X"},
            )


@requires_db
def test_both_null_accepted(db_engine, account_id):
    """T042 — amount NULL + currency NULL accepté."""
    with db_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO entreprise (id, account_id, name) VALUES (:id, :a, :n)"
            ),
            {"id": str(uuid.uuid4()), "a": account_id, "n": "Y"},
        )


@requires_db
@pytest.mark.parametrize("currency", ["XOF", "EUR", "USD"])
def test_valid_money_accepted(db_engine, account_id, currency):
    """T043 — valeurs valides (XOF/EUR/USD) acceptées."""
    with db_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO entreprise "
                "(id, account_id, name, taille_ca_amount, taille_ca_currency) "
                "VALUES (:id, :a, :n, 1500.50, :c)"
            ),
            {"id": str(uuid.uuid4()), "a": account_id, "n": f"Z{currency}", "c": currency},
        )
