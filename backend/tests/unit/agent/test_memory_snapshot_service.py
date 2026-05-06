"""F57 / US3 — Tests unit ``service.get_memory_snapshot`` (orchestration)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.chat.memory.service import (
    ThreadMemoryNotFoundError,
    get_memory_snapshot,
)

pytestmark = pytest.mark.unit


def test_get_snapshot_raises_404_when_thread_missing() -> None:
    db = MagicMock()
    with patch(
        "app.chat.memory.service.get_thread_for_account", return_value=None
    ):
        with pytest.raises(ThreadMemoryNotFoundError):
            get_memory_snapshot(
                db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
            )


def test_get_snapshot_returns_full_payload() -> None:
    db = MagicMock()
    tid = uuid.uuid4()
    aid = uuid.uuid4()
    last_compacted = datetime(2026, 5, 4, tzinfo=UTC)
    eid_1 = uuid.uuid4()
    with patch(
        "app.chat.memory.service.get_thread_for_account",
        return_value={
            "id": tid,
            "summary": "bullets",
            "last_compacted_at": last_compacted,
            "archived": False,
        },
    ), patch(
        "app.chat.memory.service.count_messages", return_value=47
    ), patch(
        "app.chat.memory.service.count_messages_with_embedding",
        return_value=32,
    ), patch(
        "app.chat.memory.service.get_entities_referenced",
        return_value=[
            {"type": "Entreprise", "id": str(eid_1), "label": "ACME"}
        ],
    ):
        snap = get_memory_snapshot(db, thread_id=tid, account_id=aid)
    assert snap.total_messages == 47
    assert snap.recent_messages_count == 15  # default cap
    assert snap.summary == "bullets"
    assert snap.vector_index_size == 32
    assert snap.last_compaction_at == last_compacted
    assert len(snap.entities_referenced) == 1
    assert snap.entities_referenced[0].type == "Entreprise"


def test_get_snapshot_skips_invalid_entity_refs() -> None:
    db = MagicMock()
    with patch(
        "app.chat.memory.service.get_thread_for_account",
        return_value={
            "id": uuid.uuid4(),
            "summary": None,
            "last_compacted_at": None,
            "archived": False,
        },
    ), patch(
        "app.chat.memory.service.count_messages", return_value=5
    ), patch(
        "app.chat.memory.service.count_messages_with_embedding", return_value=0
    ), patch(
        "app.chat.memory.service.get_entities_referenced",
        return_value=[
            {"type": "Entreprise", "id": "not-a-uuid", "label": "bad"},
            {
                "type": "Projet",
                "id": str(uuid.uuid4()),
                "label": "OK",
            },
        ],
    ):
        snap = get_memory_snapshot(
            db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
        )
    # Bad UUID skipped, OK kept
    assert len(snap.entities_referenced) == 1
    assert snap.entities_referenced[0].type == "Projet"


def test_get_snapshot_recent_count_capped_by_total() -> None:
    """``recent_messages_count`` doit être ≤ total."""
    db = MagicMock()
    with patch(
        "app.chat.memory.service.get_thread_for_account",
        return_value={
            "id": uuid.uuid4(),
            "summary": None,
            "last_compacted_at": None,
            "archived": False,
        },
    ), patch(
        "app.chat.memory.service.count_messages", return_value=3
    ), patch(
        "app.chat.memory.service.count_messages_with_embedding", return_value=0
    ), patch(
        "app.chat.memory.service.get_entities_referenced", return_value=[]
    ):
        snap = get_memory_snapshot(
            db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
        )
    assert snap.recent_messages_count == 3
