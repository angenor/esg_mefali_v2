"""F57 / US9 — Tests unit ``recall_log.write_recall_log`` & ``flush_entries``.

Couvre la sérialisation JSON top_scores + la conversion thread_id composite,
+ le best-effort en cas d'erreur DB (pas d'exception remontée).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.agent.memory import recall_log

pytestmark = pytest.mark.unit


def test_write_recall_log_invalid_recall_type_raises() -> None:
    db = MagicMock()
    with pytest.raises(ValueError):
        recall_log.write_recall_log(
            db,
            recall_type="bogus",
            thread_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            query_hash="x",
            top_k=1,
            top_scores=[],
            latency_ms=0,
        )


def test_write_recall_log_returns_uuid_on_success() -> None:
    db = MagicMock()
    out = recall_log.write_recall_log(
        db,
        recall_type="auto",
        thread_id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        query_hash="h",
        top_k=3,
        top_scores=[{"message_id": str(uuid.uuid4()), "score": 0.9}],
        latency_ms=42,
    )
    assert isinstance(out, uuid.UUID)


def test_write_recall_log_handles_composite_thread_id() -> None:
    db = MagicMock()
    a = uuid.uuid4()
    b = uuid.uuid4()
    out = recall_log.write_recall_log(
        db,
        recall_type="tool",
        thread_id=f"{a}:{b}",
        account_id=uuid.uuid4(),
        query_hash="h",
        top_k=1,
        top_scores=[],
        latency_ms=10,
    )
    assert isinstance(out, uuid.UUID)


def test_write_recall_log_invalid_thread_returns_none() -> None:
    db = MagicMock()
    out = recall_log.write_recall_log(
        db,
        recall_type="auto",
        thread_id=":",
        account_id=uuid.uuid4(),
        query_hash="h",
        top_k=1,
        top_scores=[],
        latency_ms=10,
    )
    assert out is None


def test_write_recall_log_db_error_returns_none() -> None:
    db = MagicMock()
    db.execute.side_effect = RuntimeError("DB down")
    out = recall_log.write_recall_log(
        db,
        recall_type="auto",
        thread_id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        query_hash="h",
        top_k=1,
        top_scores=[],
        latency_ms=10,
    )
    assert out is None


def test_flush_entries_returns_count_written() -> None:
    db = MagicMock()
    entries = [
        {
            "recall_type": "auto",
            "thread_id": str(uuid.uuid4()),
            "account_id": str(uuid.uuid4()),
            "query_hash": "h1",
            "top_k": 3,
            "top_scores": [],
            "latency_ms": 12,
            "agent_run_id": None,
        },
        {
            "recall_type": "tool",
            "thread_id": str(uuid.uuid4()),
            "account_id": str(uuid.uuid4()),
            "query_hash": "h2",
            "top_k": 1,
            "top_scores": [{"message_id": str(uuid.uuid4()), "score": 0.5}],
            "latency_ms": 5,
            "agent_run_id": str(uuid.uuid4()),
        },
    ]
    n = recall_log.flush_entries(db, entries)
    assert n == 2


def test_flush_entries_skips_invalid_entry_continues_others() -> None:
    db = MagicMock()
    entries = [
        {
            # missing keys → skipped
            "recall_type": "auto",
        },
        {
            "recall_type": "auto",
            "thread_id": str(uuid.uuid4()),
            "account_id": str(uuid.uuid4()),
            "query_hash": "h",
            "top_k": 1,
            "top_scores": [],
            "latency_ms": 0,
            "agent_run_id": None,
        },
    ]
    n = recall_log.flush_entries(db, entries)
    assert n == 1


def test_flush_entries_empty_list_returns_zero() -> None:
    db = MagicMock()
    assert recall_log.flush_entries(db, []) == 0
