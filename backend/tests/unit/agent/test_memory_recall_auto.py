"""F57 / US1 — Tests unit du nœud ``recall_memory``.

Couvre RM-001..RM-006 (mode dégradé, court terme, long terme, summary).
On mocke ``SessionLocal`` pour isoler du DB.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.agent.memory.long_term import LongTermMatch
from app.agent.nodes.recall_memory import (
    PREFIX_LONG_TERM,
    PREFIX_SUMMARY,
    node_recall_memory,
)
from app.agent.state import AgentState, ContextJson

pytestmark = pytest.mark.unit


def _make_state(*, user_message: str = "Reprends solaire") -> AgentState:
    aid = uuid4()
    cid = uuid4()
    return AgentState(
        thread_id=f"{aid}:{cid}",
        account_id=aid,
        user_id=uuid4(),
        user_message=user_message,
        context_json=ContextJson(page_route="/chat"),
    )


def _mk_session_stub(*, fail: bool = False) -> Any:
    class _Sess:
        def execute(self, *a: Any, **kw: Any) -> Any:
            if fail:
                raise RuntimeError("DB down")
            return None

        def close(self) -> None:
            pass

    return _Sess()


def test_rm_001_thread_lt_15_no_embed_no_recall_log() -> None:
    """RM-001 — Thread < 15 msgs : pas d'embedding, pas de recall_log entry."""
    state = _make_state()
    embed_calls = []

    def fake_embed(texts):  # noqa: ANN001
        embed_calls.append(texts)
        return [[0.1] * 1024]

    with patch(
        "app.agent.nodes.recall_memory.SessionLocal",
        return_value=_mk_session_stub(),
    ), patch(
        "app.agent.nodes.recall_memory.set_db_session_context"
    ), patch(
        "app.agent.memory.long_term.fetch_recent_messages",
        return_value=[
            {
                "id": str(uuid4()),
                "role": "user",
                "content": "Bonjour",
                "created_at": datetime.now(UTC),
            }
        ],
    ), patch(
        "app.agent.memory.long_term.count_thread_messages",
        return_value=5,
    ), patch(
        "app.agent.nodes.recall_memory._get_thread_summary",
        return_value=None,
    ), patch(
        "app.embeddings_client.embed", side_effect=fake_embed
    ):
        patch_dict = asyncio.run(node_recall_memory(state))

    assert "recall_log_entries" not in patch_dict
    assert embed_calls == []
    assert "messages" in patch_dict
    assert len(patch_dict["messages"]) == 1


def test_rm_002_thread_50_msgs_with_long_term_match() -> None:
    """RM-002 — Thread 50 msgs, query trouve un souvenir → 1 entry recall_log."""
    state = _make_state()
    recent = [
        {
            "id": str(uuid4()),
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"msg-{i}",
            "created_at": datetime.now(UTC),
        }
        for i in range(15)
    ]
    found = LongTermMatch(
        message_id=uuid4(),
        role="user",
        content="On parlait de solaire 50 kWc",
        created_at=datetime.now(UTC),
        score=0.85,
    )

    with patch(
        "app.agent.nodes.recall_memory.SessionLocal",
        return_value=_mk_session_stub(),
    ), patch(
        "app.agent.nodes.recall_memory.set_db_session_context"
    ), patch(
        "app.agent.memory.long_term.fetch_recent_messages",
        return_value=recent,
    ), patch(
        "app.agent.memory.long_term.count_thread_messages",
        return_value=50,
    ), patch(
        "app.agent.memory.long_term.search_long_term",
        return_value=[found],
    ), patch(
        "app.agent.nodes.recall_memory._get_thread_summary",
        return_value=None,
    ), patch(
        "app.embeddings_client.embed", return_value=[[0.5] * 1024]
    ):
        patch_dict = asyncio.run(node_recall_memory(state))

    assert "messages" in patch_dict
    msgs = patch_dict["messages"]
    # 1 souvenir (system) + 15 court terme = 16
    assert len(msgs) == 16
    # Le 1er msg doit contenir le préfixe long terme
    assert PREFIX_LONG_TERM in str(msgs[0].content)
    # Une recall_log_entry staged (auto)
    assert "recall_log_entries" in patch_dict
    entries = patch_dict["recall_log_entries"]
    assert len(entries) == 1
    assert entries[0]["recall_type"] == "auto"


def test_rm_003_summary_present_inserted_first() -> None:
    """RM-003 — Si chat_thread.summary défini, inséré en TOUT premier."""
    state = _make_state()
    recent = [
        {
            "id": str(uuid4()),
            "role": "assistant",
            "content": "Salut",
            "created_at": datetime.now(UTC),
        }
    ]
    with patch(
        "app.agent.nodes.recall_memory.SessionLocal",
        return_value=_mk_session_stub(),
    ), patch(
        "app.agent.nodes.recall_memory.set_db_session_context"
    ), patch(
        "app.agent.memory.long_term.fetch_recent_messages",
        return_value=recent,
    ), patch(
        "app.agent.memory.long_term.count_thread_messages",
        return_value=200,
    ), patch(
        "app.agent.memory.long_term.search_long_term",
        return_value=[],
    ), patch(
        "app.agent.nodes.recall_memory._get_thread_summary",
        return_value="bullet 1\nbullet 2",
    ), patch(
        "app.embeddings_client.embed", return_value=[[0.5] * 1024]
    ):
        patch_dict = asyncio.run(node_recall_memory(state))

    msgs = patch_dict["messages"]
    assert PREFIX_SUMMARY in str(msgs[0].content)


def test_rm_004_voyage_down_no_crash() -> None:
    """RM-004 — Voyage API down → 15 derniers OK, no crash, no exception."""
    state = _make_state()
    recent = [
        {
            "id": str(uuid4()),
            "role": "user",
            "content": f"msg-{i}",
            "created_at": datetime.now(UTC),
        }
        for i in range(15)
    ]
    with patch(
        "app.agent.nodes.recall_memory.SessionLocal",
        return_value=_mk_session_stub(),
    ), patch(
        "app.agent.nodes.recall_memory.set_db_session_context"
    ), patch(
        "app.agent.memory.long_term.fetch_recent_messages",
        return_value=recent,
    ), patch(
        "app.agent.memory.long_term.count_thread_messages",
        return_value=50,
    ), patch(
        "app.agent.nodes.recall_memory._get_thread_summary",
        return_value=None,
    ), patch(
        "app.embeddings_client.embed",
        side_effect=RuntimeError("Voyage 500"),
    ):
        patch_dict = asyncio.run(node_recall_memory(state))

    # 15 messages chronologiques OK, pas d'exception
    assert "messages" in patch_dict
    assert len(patch_dict["messages"]) == 15


def test_rm_005_idempotent_skip_when_already_loaded() -> None:
    """Si state.messages contient déjà ≥ 2 HumanMessage → skip (sécurité)."""
    from langchain_core.messages import HumanMessage

    state = _make_state()
    state.messages = [HumanMessage("a"), HumanMessage("b")]
    out = asyncio.run(node_recall_memory(state))
    assert out == {}
