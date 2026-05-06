"""F57 / US2 — Tests unit du handler ``recall_history``.

Schémas Pydantic strict (P9), tronquage budget tokens, NFR-008 cache.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agent.handlers.recall_history import (
    PREVIEW_PER_MATCH_CHARS,
    RecallHistoryArgs,
    RecallHistoryMatch,
    RecallHistoryResult,
    handle_recall_history,
)
from app.agent.memory.long_term import LongTermMatch
from app.agent.state import AgentState, ContextJson

pytestmark = pytest.mark.unit


def _make_state() -> AgentState:
    aid = uuid4()
    cid = uuid4()
    return AgentState(
        thread_id=f"{aid}:{cid}",
        account_id=aid,
        user_id=uuid4(),
        user_message="hello",
        context_json=ContextJson(page_route="/chat"),
    )


def test_args_extra_forbid_rejects_unknown_keys() -> None:
    with pytest.raises(ValidationError):
        RecallHistoryArgs(query="hello", limit=5, foo="bar")  # type: ignore[call-arg]


def test_args_query_min_length() -> None:
    with pytest.raises(ValidationError):
        RecallHistoryArgs(query="")


def test_args_limit_max_10() -> None:
    with pytest.raises(ValidationError):
        RecallHistoryArgs(query="x", limit=20)
    with pytest.raises(ValidationError):
        RecallHistoryArgs(query="x", limit=0)


def test_args_default_limit_is_5() -> None:
    a = RecallHistoryArgs(query="hello")
    assert a.limit == 5


def test_match_clamps_score_in_0_1() -> None:
    """``score`` doit être ∈ [0, 1] (Field constraint)."""
    with pytest.raises(ValidationError):
        RecallHistoryMatch(
            message_id=uuid4(),
            role="user",
            content_preview="x",
            score=1.5,
            created_at=datetime.now(UTC),
        )


def test_handle_returns_empty_when_db_unavailable() -> None:
    """Si la session DB ne peut pas être ouverte → matches=[] (NFR-008)."""
    state = _make_state()

    with patch(
        "app.agent.handlers.recall_history._get_session", return_value=None
    ):
        out = asyncio.run(
            handle_recall_history(
                RecallHistoryArgs(query="ping"), state=state
            )
        )
    assert isinstance(out, RecallHistoryResult)
    assert out.matches == []
    assert out.truncated is False


def test_handle_returns_empty_on_voyage_down() -> None:
    """Voyage down (embedding=None) → matches=[]."""
    state = _make_state()

    class _FakeSess:
        def execute(self, *a: Any, **kw: Any) -> Any:
            return None

        def close(self) -> None:
            pass

    with patch(
        "app.agent.handlers.recall_history._get_session",
        return_value=_FakeSess(),
    ), patch(
        "app.agent.memory.embedding_cache.get_or_compute",
        new=_async_return(None),
    ):
        out = asyncio.run(
            handle_recall_history(
                RecallHistoryArgs(query="ping"), state=state
            )
        )
    assert out.matches == []


def test_handle_truncates_long_contents() -> None:
    """Match avec content > PREVIEW_PER_MATCH_CHARS → ``truncated=True``."""
    state = _make_state()
    big_text = "X" * (PREVIEW_PER_MATCH_CHARS + 200)
    match = LongTermMatch(
        message_id=uuid4(),
        role="user",
        content=big_text,
        created_at=datetime.now(UTC),
        score=0.85,
    )

    class _FakeSess:
        def execute(self, *a: Any, **kw: Any) -> Any:
            return None

        def close(self) -> None:
            pass

    with patch(
        "app.agent.handlers.recall_history._get_session",
        return_value=_FakeSess(),
    ), patch(
        "app.agent.memory.embedding_cache.get_or_compute",
        new=_async_return([0.1] * 1024),
    ), patch(
        "app.agent.memory.long_term.search_long_term",
        return_value=[match],
    ):
        out = asyncio.run(
            handle_recall_history(
                RecallHistoryArgs(query="ping", limit=3), state=state
            )
        )
    assert out.truncated is True
    assert len(out.matches) == 1
    assert len(out.matches[0].content_preview) <= PREVIEW_PER_MATCH_CHARS
    assert out.matches[0].content_preview.endswith("…")


def test_handle_stages_recall_log_entry_tool() -> None:
    """US9 — chaque call recall_history doit stager une entry recall_type='tool'."""
    state = _make_state()
    assert state.recall_log_entries == []
    match = LongTermMatch(
        message_id=uuid4(),
        role="assistant",
        content="ok",
        created_at=datetime.now(UTC),
        score=0.5,
    )

    class _FakeSess:
        def execute(self, *a: Any, **kw: Any) -> Any:
            return None

        def close(self) -> None:
            pass

    with patch(
        "app.agent.handlers.recall_history._get_session",
        return_value=_FakeSess(),
    ), patch(
        "app.agent.memory.embedding_cache.get_or_compute",
        new=_async_return([0.1] * 1024),
    ), patch(
        "app.agent.memory.long_term.search_long_term",
        return_value=[match],
    ):
        asyncio.run(
            handle_recall_history(
                RecallHistoryArgs(query="ping"), state=state
            )
        )
    assert len(state.recall_log_entries) == 1
    entry = state.recall_log_entries[0]
    assert entry["recall_type"] == "tool"
    assert entry["query_hash"]
    assert "top_scores" in entry


def test_register_idempotent() -> None:
    """Le register doit pouvoir être appelé deux fois sans crash."""
    from app.agent.handlers import recall_history as rh
    from app.agent.nodes.dispatch_tool import _REINVOKE_HANDLERS

    rh.register()
    rh.register()
    assert "recall_history" in _REINVOKE_HANDLERS


def _async_return(value):  # noqa: ANN001
    """Helper : renvoie une coroutine qui retourne ``value``."""

    async def _fn(*a, **kw):  # noqa: ANN001
        return value

    return _fn
