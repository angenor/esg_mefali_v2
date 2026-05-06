"""F57 — Tests unit du module ``app.agent.memory.long_term``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.agent.memory import long_term

pytestmark = pytest.mark.unit


def test_conv_uuid_from_composite_format() -> None:
    a = uuid.uuid4()
    b = uuid.uuid4()
    out = long_term._conv_uuid_from_thread_id(f"{a}:{b}")
    assert out == str(b)


def test_conv_uuid_from_simple_uuid_string() -> None:
    a = uuid.uuid4()
    out = long_term._conv_uuid_from_thread_id(str(a))
    assert out == str(a)


def test_conv_uuid_from_uuid_obj() -> None:
    a = uuid.uuid4()
    out = long_term._conv_uuid_from_thread_id(a)
    assert out == str(a)


def test_search_long_term_empty_embedding_returns_empty() -> None:
    db = MagicMock()
    out = long_term.search_long_term(
        db,
        thread_id=str(uuid.uuid4()),
        account_id=uuid.uuid4(),
        query_embedding=[],
    )
    assert out == []
    db.execute.assert_not_called()


def test_search_long_term_invalid_thread_returns_empty() -> None:
    db = MagicMock()
    out = long_term.search_long_term(
        db,
        thread_id=":",  # parse → suffix vide
        account_id=uuid.uuid4(),
        query_embedding=[0.1] * 1024,
    )
    assert out == []


def test_search_long_term_db_error_falls_back_to_empty() -> None:
    """Mode dégradé pgvector : DB error → liste vide, pas d'exception."""
    db = MagicMock()
    db.execute.side_effect = RuntimeError("pgvector down")
    out = long_term.search_long_term(
        db,
        thread_id=str(uuid.uuid4()),
        account_id=uuid.uuid4(),
        query_embedding=[0.1] * 1024,
    )
    assert out == []


def test_search_long_term_parses_rows_into_matches() -> None:
    db = MagicMock()
    mid = uuid.uuid4()
    rows = [
        {
            "id": str(mid),
            "role": "user",
            "content": "hello",
            "created_at": datetime.now(UTC),
            "score": 0.9,
        }
    ]
    proxy = MagicMock()
    mappings = MagicMock()
    mappings.all.return_value = rows
    proxy.mappings.return_value = mappings
    db.execute.return_value = proxy
    out = long_term.search_long_term(
        db,
        thread_id=str(uuid.uuid4()),
        account_id=uuid.uuid4(),
        query_embedding=[0.1] * 1024,
        limit=3,
        threshold=0.5,
    )
    assert len(out) == 1
    assert out[0].message_id == mid
    assert out[0].role == "user"
    assert 0.0 <= out[0].score <= 1.0


def test_count_thread_messages_returns_int() -> None:
    db = MagicMock()
    proxy = MagicMock()
    proxy.first.return_value = (47,)
    db.execute.return_value = proxy
    n = long_term.count_thread_messages(
        db, thread_id=str(uuid.uuid4()), account_id=uuid.uuid4()
    )
    assert n == 47


def test_count_thread_messages_invalid_thread_returns_zero() -> None:
    db = MagicMock()
    n = long_term.count_thread_messages(
        db, thread_id=":", account_id=uuid.uuid4()
    )
    assert n == 0


def test_fetch_recent_messages_returns_chronological_asc() -> None:
    db = MagicMock()
    rows_desc = [
        {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": "msg-3",
            "created_at": datetime.now(UTC),
        },
        {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": "msg-2",
            "created_at": datetime.now(UTC),
        },
        {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": "msg-1",
            "created_at": datetime.now(UTC),
        },
    ]
    proxy = MagicMock()
    mappings = MagicMock()
    mappings.all.return_value = rows_desc
    proxy.mappings.return_value = mappings
    db.execute.return_value = proxy
    out = long_term.fetch_recent_messages(
        db, thread_id=str(uuid.uuid4()), account_id=uuid.uuid4(), limit=3
    )
    # La fonction retourne reversed → asc chronologique
    assert [r["content"] for r in out] == ["msg-1", "msg-2", "msg-3"]


def test_fetch_recent_message_ids_returns_list() -> None:
    db = MagicMock()
    ids = [(str(uuid.uuid4()),) for _ in range(5)]
    proxy = MagicMock()
    proxy.all.return_value = ids
    db.execute.return_value = proxy
    out = long_term.fetch_recent_message_ids(
        db, thread_id=str(uuid.uuid4()), account_id=uuid.uuid4(), limit=10
    )
    assert len(out) == 5
