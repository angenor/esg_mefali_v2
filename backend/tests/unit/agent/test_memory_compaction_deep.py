"""F57 / US6 — Tests deep coverage du compacteur."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.agent.memory import compactors

pytestmark = pytest.mark.unit


def _stub_session(rowcount: int = 1) -> Any:
    sess = MagicMock()
    res = MagicMock()
    res.rowcount = rowcount
    sess.execute.return_value = res
    sess.commit.return_value = None
    sess.rollback.return_value = None
    sess.close.return_value = None
    return sess


def test_try_acquire_lock_returns_true_on_rowcount_gt_0() -> None:
    sess = _stub_session(rowcount=1)
    assert compactors._try_acquire_lock(
        sess, thread_id=uuid4(), account_id=uuid4()
    )


def test_try_acquire_lock_returns_false_on_rowcount_0() -> None:
    sess = _stub_session(rowcount=0)
    assert not compactors._try_acquire_lock(
        sess, thread_id=uuid4(), account_id=uuid4()
    )


def test_select_batch_message_ids_returns_strings() -> None:
    sess = MagicMock()
    res = MagicMock()
    ids = [(str(uuid4()),) for _ in range(3)]
    res.all.return_value = ids
    sess.execute.return_value = res
    out = compactors._select_batch_message_ids(
        sess, thread_id=uuid4(), account_id=uuid4(), batch_size=3
    )
    assert len(out) == 3
    assert all(isinstance(x, str) for x in out)


def test_fetch_messages_for_summary_empty_ids_returns_empty() -> None:
    sess = MagicMock()
    out = compactors._fetch_messages_for_summary(sess, message_ids=[])
    assert out == []


def test_fetch_messages_for_summary_returns_dicts() -> None:
    sess = MagicMock()
    rows = [
        {"role": "user", "content": "msg-1", "created_at": "2026-01-01"}
    ]
    proxy = MagicMock()
    mappings = MagicMock()
    mappings.all.return_value = rows
    proxy.mappings.return_value = mappings
    sess.execute.return_value = proxy
    out = compactors._fetch_messages_for_summary(
        sess, message_ids=[str(uuid4())]
    )
    assert len(out) == 1
    assert out[0]["role"] == "user"


def test_llm_summarize_returns_none_on_exception(monkeypatch) -> None:
    class _Boom:
        @property
        def chat(self):  # noqa: ANN201
            raise RuntimeError("LLM down")

    monkeypatch.setattr("app.llm_client.get_llm_client", lambda: _Boom())
    out = compactors._llm_summarize_messages(
        msgs=[{"role": "user", "content": "abc"}], max_tokens=500
    )
    assert out is None


def test_llm_summarize_empty_msgs_returns_none() -> None:
    out = compactors._llm_summarize_messages(msgs=[], max_tokens=500)
    assert out is None


def test_release_lock_no_exception() -> None:
    sess = _stub_session()
    compactors._release_lock(sess, thread_id=uuid4(), account_id=uuid4())
    assert sess.execute.called


def test_release_lock_swallows_db_error() -> None:
    sess = MagicMock()
    sess.execute.side_effect = RuntimeError("DB down")
    # Doit ne PAS lever
    compactors._release_lock(sess, thread_id=uuid4(), account_id=uuid4())


def test_write_audit_compaction_returns_uuid() -> None:
    sess = _stub_session()
    audit_id = compactors._write_audit_compaction(
        sess,
        thread_id=uuid4(),
        account_id=uuid4(),
        user_id=uuid4(),
        batch_size=10,
        new_summary_chars=300,
    )
    import uuid as uuidlib

    assert isinstance(audit_id, uuidlib.UUID)


def test_compact_thread_handles_write_failure_rolls_back() -> None:
    """Si UPDATE summary throw → rollback + retourne 0 (pas d'exception)."""
    sess = MagicMock()
    sess.commit.return_value = None
    sess.rollback.return_value = None
    sess.close.return_value = None
    res_lock = MagicMock(rowcount=1)

    import app.db as _db

    ids = [str(uuid4()) for _ in range(3)]
    # Flux : SET LOCAL (1), try_acquire_lock UPDATE (2), puis UPDATE
    # chat_thread (3) qui doit échouer. On retourne res_lock pour les
    # deux premiers et on lève sur le 3ème.
    calls = {"n": 0}

    def _exec(*a: Any, **kw: Any) -> Any:
        calls["n"] += 1
        if calls["n"] <= 2:
            return res_lock
        raise RuntimeError("UPDATE failed")

    sess.execute.side_effect = _exec

    with patch.object(_db, "SessionLocal", return_value=sess), patch.object(
        compactors, "_select_batch_message_ids", return_value=ids
    ), patch.object(
        compactors,
        "_fetch_messages_for_summary",
        return_value=[{"role": "user", "content": "x"}],
    ), patch.object(
        compactors, "_llm_summarize_messages", return_value="bullets"
    ):
        n = compactors.compact_thread(
            account_id=uuid4(), thread_id=uuid4()
        )
    assert n == 0
    sess.rollback.assert_called()
