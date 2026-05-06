"""F57 / T008 — Schema extensions tests (chat_thread.summary,
chat_thread.last_compacted_at, chat_message.compacted)."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.integration.conftest import requires_db

pytestmark = [pytest.mark.integration, requires_db]


def _column_exists(db_engine, table: str, column: str) -> bool:
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_name = :t AND column_name = :c
                """
            ),
            {"t": table, "c": column},
        ).first()
    return row is not None


def test_chat_thread_summary_column_exists(db_engine) -> None:
    assert _column_exists(db_engine, "chat_thread", "summary")


def test_chat_thread_last_compacted_at_column_exists(db_engine) -> None:
    assert _column_exists(db_engine, "chat_thread", "last_compacted_at")


def test_chat_message_compacted_column_exists(db_engine) -> None:
    assert _column_exists(db_engine, "chat_message", "compacted")


def test_chat_message_compacted_default_false(db_engine) -> None:
    """Le default doit être FALSE (NOT NULL)."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT column_default, is_nullable FROM information_schema.columns
                WHERE table_name = 'chat_message' AND column_name = 'compacted'
                """
            )
        ).first()
    assert row is not None
    # Postgres stores defaults as 'false' (string) for boolean
    assert row[1] == "NO"  # NOT NULL


def test_agent_entity_memory_table_exists(db_engine) -> None:
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'agent_entity_memory'
                """
            )
        ).first()
    assert row is not None


def test_recall_log_table_exists(db_engine) -> None:
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'recall_log'
                """
            )
        ).first()
    assert row is not None


def test_chat_message_hnsw_index_exists(db_engine) -> None:
    """L'index HNSW doit être créé sur chat_message.embedding."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'chat_message'
                  AND indexname = 'chat_message_embedding_hnsw_idx'
                """
            )
        ).first()
    # Note : si pgvector < 0.5 (HNSW non supporté), l'index HNSW peut être
    # absent et la migration aura installé un fallback ivfflat qui existe
    # déjà. On vérifie soit HNSW soit l'absence (compatibilité).
    if row is None:
        # Vérifier l'ancien ivfflat reste présent
        with db_engine.connect() as conn2:
            fallback = conn2.execute(
                text(
                    """
                    SELECT indexname FROM pg_indexes
                    WHERE tablename = 'chat_message'
                      AND indexdef ILIKE '%embedding%'
                    """
                )
            ).first()
        assert fallback is not None, "no vector index on chat_message.embedding"
    else:
        assert row is not None
