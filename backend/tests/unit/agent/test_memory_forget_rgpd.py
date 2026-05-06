"""F57 / US4 — Tests unit du service ``forget_thread_memory``.

Vérifie l'orchestration : purge embeddings + clear summary + write audit
+ message count, sans toucher au content (P3) ni à entity_memory.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.chat.memory.service import (
    ThreadMemoryNotFoundError,
    forget_thread_memory,
)

pytestmark = pytest.mark.unit


def test_forget_raises_404_when_thread_not_found() -> None:
    db = MagicMock()
    with patch(
        "app.chat.memory.service.get_thread_for_account", return_value=None
    ):
        with pytest.raises(ThreadMemoryNotFoundError):
            forget_thread_memory(
                db,
                thread_id=uuid.uuid4(),
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )


def test_forget_returns_full_result() -> None:
    db = MagicMock()
    tid = uuid.uuid4()
    aid = uuid.uuid4()
    uid = uuid.uuid4()
    audit = uuid.uuid4()
    with patch(
        "app.chat.memory.service.get_thread_for_account",
        return_value={"id": tid, "summary": "x", "last_compacted_at": None},
    ), patch(
        "app.chat.memory.service.purge_thread_embeddings", return_value=42
    ), patch(
        "app.chat.memory.service.clear_thread_summary",
        return_value=(True, False),
    ), patch(
        "app.chat.memory.service.write_audit_memory_forget", return_value=audit
    ), patch(
        "app.chat.memory.service.count_messages", return_value=50
    ):
        result = forget_thread_memory(
            db, thread_id=tid, account_id=aid, user_id=uid
        )
    assert result.thread_id == tid
    assert result.embeddings_purged == 42
    assert result.summary_cleared is True
    assert result.last_compaction_cleared is False
    assert result.messages_kept_for_audit == 50
    assert result.agent_entity_memory_unchanged is True
    assert result.audit_log_id == audit


def test_forget_idempotent_when_no_embeddings_or_summary() -> None:
    db = MagicMock()
    tid = uuid.uuid4()
    audit = uuid.uuid4()
    with patch(
        "app.chat.memory.service.get_thread_for_account",
        return_value={"id": tid, "summary": None, "last_compacted_at": None},
    ), patch(
        "app.chat.memory.service.purge_thread_embeddings", return_value=0
    ), patch(
        "app.chat.memory.service.clear_thread_summary",
        return_value=(False, False),
    ), patch(
        "app.chat.memory.service.write_audit_memory_forget", return_value=audit
    ), patch(
        "app.chat.memory.service.count_messages", return_value=0
    ):
        result = forget_thread_memory(
            db,
            thread_id=tid,
            account_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
    assert result.embeddings_purged == 0
    assert result.summary_cleared is False
