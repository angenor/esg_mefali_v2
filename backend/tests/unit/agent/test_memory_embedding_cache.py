"""F57 / US8 — Tests cache embedding par tour."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest

from app.agent.memory import embedding_cache
from app.agent.state import AgentState, ContextJson

pytestmark = pytest.mark.unit


def _make_state() -> AgentState:
    aid = uuid4()
    cid = uuid4()
    uid = uuid4()
    return AgentState(
        thread_id=f"{aid}:{cid}",
        account_id=aid,
        user_id=uid,
        user_message="hello",
        context_json=ContextJson(page_route="/chat"),
    )


def test_make_key_includes_thread_id() -> None:
    """US5 / US8 — la clé inclut thread_id (anti-fuite cross-thread)."""
    a = uuid4()
    b = uuid4()
    k1 = embedding_cache.make_key(str(a), "hello")
    k2 = embedding_cache.make_key(str(b), "hello")
    assert k1 != k2
    # même thread + même query → même clé
    assert embedding_cache.make_key(str(a), "hello") == k1


def test_set_get_cached_round_trip() -> None:
    state = _make_state()
    assert embedding_cache.get_cached(state, state.thread_id, "q") is None
    embedding_cache.set_cached(state, state.thread_id, "q", [0.1] * 1024)
    out = embedding_cache.get_cached(state, state.thread_id, "q")
    assert out is not None
    assert len(out) == 1024


def test_get_or_compute_calls_embed_only_once() -> None:
    state = _make_state()
    calls: list[list[str]] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        calls.append(list(texts))
        return [[0.42] * 1024]

    vec = asyncio.run(
        embedding_cache.get_or_compute(
            state, thread_id=state.thread_id, query="q", embed_fn=fake_embed
        )
    )
    assert vec is not None and len(vec) == 1024
    # 2nd call HITS cache
    vec2 = asyncio.run(
        embedding_cache.get_or_compute(
            state, thread_id=state.thread_id, query="q", embed_fn=fake_embed
        )
    )
    assert vec2 == vec
    assert len(calls) == 1, "embed must only be called once (cache HIT)"


def test_get_or_compute_voyage_down_returns_none() -> None:
    state = _make_state()

    def boom(texts: list[str]) -> list[list[float]]:
        raise RuntimeError("Voyage down")

    out = asyncio.run(
        embedding_cache.get_or_compute(
            state, thread_id=state.thread_id, query="q", embed_fn=boom
        )
    )
    assert out is None


def test_state_embedding_cache_excluded_from_dump() -> None:
    """US8 — embedding_cache est exclu du checkpointer (exclude=True)."""
    state = _make_state()
    embedding_cache.set_cached(state, state.thread_id, "q", [0.1] * 1024)
    state.recall_log_entries.append({"hi": "there"})
    dumped: Any = state.model_dump()
    assert "embedding_cache" not in dumped
    assert "recall_log_entries" not in dumped


def test_get_or_compute_distinct_queries_two_calls() -> None:
    state = _make_state()
    calls: list[str] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        calls.extend(texts)
        return [[0.5] * 1024]

    asyncio.run(
        embedding_cache.get_or_compute(
            state, thread_id=state.thread_id, query="q1", embed_fn=fake_embed
        )
    )
    asyncio.run(
        embedding_cache.get_or_compute(
            state, thread_id=state.thread_id, query="q2", embed_fn=fake_embed
        )
    )
    assert len(calls) == 2
