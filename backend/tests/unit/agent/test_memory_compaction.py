"""F57 / US6 — Tests unit du compacteur (lock optimiste, LLM, audit).

Tests pure unit avec mocks DB ; les vrais UPDATE/RLS sont validés en
intégration (test_memory_rls_recall_log + test_memory_schema_extensions).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit


def _make_session_stub(rowcount: int = 1) -> Any:
    sess = MagicMock()
    res_obj = MagicMock()
    res_obj.rowcount = rowcount
    sess.execute.return_value = res_obj
    sess.commit.return_value = None
    sess.rollback.return_value = None
    sess.close.return_value = None
    return sess


def test_compact_thread_returns_0_when_lock_busy() -> None:
    """Si un autre worker tient le lock (rowcount=0) → no-op."""
    from app.agent.memory.compactors import compact_thread

    sess = _make_session_stub(rowcount=0)

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=sess):
        n = compact_thread(account_id=uuid4(), thread_id=uuid4())
    assert n == 0


def test_compact_thread_returns_0_when_no_messages() -> None:
    """Lock acquis mais 0 messages à compacter → no-op."""
    from app.agent.memory import compactors

    sess = _make_session_stub(rowcount=1)

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=sess), patch.object(
        compactors, "_select_batch_message_ids", return_value=[]
    ):
        n = compactors.compact_thread(account_id=uuid4(), thread_id=uuid4())
    assert n == 0


def test_compact_thread_releases_lock_when_llm_down() -> None:
    """LLM down → release lock + retourne 0."""
    from app.agent.memory import compactors

    sess = _make_session_stub(rowcount=1)

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=sess), patch.object(
        compactors,
        "_select_batch_message_ids",
        return_value=[str(uuid4()), str(uuid4())],
    ), patch.object(
        compactors,
        "_fetch_messages_for_summary",
        return_value=[{"role": "user", "content": "x"}],
    ), patch.object(
        compactors, "_llm_summarize_messages", return_value=None
    ), patch.object(
        compactors, "_release_lock"
    ) as mock_release:
        n = compactors.compact_thread(account_id=uuid4(), thread_id=uuid4())
    assert n == 0
    mock_release.assert_called_once()


def test_compact_thread_writes_summary_and_audit_when_llm_ok() -> None:
    from app.agent.memory import compactors

    sess = _make_session_stub(rowcount=1)
    ids = [str(uuid4()) for _ in range(3)]

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=sess), patch.object(
        compactors, "_select_batch_message_ids", return_value=ids
    ), patch.object(
        compactors,
        "_fetch_messages_for_summary",
        return_value=[{"role": "user", "content": "abc"}],
    ), patch.object(
        compactors, "_llm_summarize_messages", return_value="- bullet 1\n- bullet 2"
    ), patch.object(
        compactors, "_write_audit_compaction", return_value=uuid4()
    ) as mock_audit:
        n = compactors.compact_thread(account_id=uuid4(), thread_id=uuid4())
    assert n == 3
    mock_audit.assert_called_once()
