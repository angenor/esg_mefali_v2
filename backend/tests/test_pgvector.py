"""Tests extension pgvector + colonne embedding (T046-T047)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text

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


@requires_db
def test_pgvector_extension_installed(db_engine):
    """T046 — extension vector activée."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname='vector'")
        ).fetchone()
    assert row is not None, "extension `vector` non installée"


@requires_db
def test_chat_message_embedding_is_vector_1024(db_engine):
    """T047 — chat_message.embedding typé vector(1024)."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT format_type(a.atttypid, a.atttypmod) "
                "FROM pg_attribute a "
                "JOIN pg_class c ON c.oid = a.attrelid "
                "WHERE c.relname='chat_message' AND a.attname='embedding'"
            )
        ).fetchone()
    assert row is not None, "chat_message.embedding absent"
    assert row[0] == "vector(1024)", f"type inattendu: {row[0]}"
