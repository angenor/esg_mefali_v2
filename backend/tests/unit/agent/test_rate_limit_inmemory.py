"""F55 / T102 — Unit tests ``InMemoryRateLimitStore``."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.agent.rate_limit import (
    InMemoryRateLimitStore,
    _default_limits,
    resolve_limit,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_first_call_allowed():
    store = InMemoryRateLimitStore()
    aid = uuid4()
    decision = await store.check_and_increment(aid, "update_company_profile", 30)
    assert decision.allowed is True
    assert decision.remaining == 29
    assert decision.reason == "ok"


@pytest.mark.asyncio
async def test_31st_call_refused():
    store = InMemoryRateLimitStore()
    aid = uuid4()
    for _ in range(30):
        await store.check_and_increment(aid, "update_*", 30)
    decision = await store.check_and_increment(aid, "update_*", 30)
    assert decision.allowed is False
    assert decision.reason == "exceeded"


@pytest.mark.asyncio
async def test_distinct_accounts_independent():
    store = InMemoryRateLimitStore()
    a1, a2 = uuid4(), uuid4()
    for _ in range(30):
        await store.check_and_increment(a1, "delete_*", 30)
    decision = await store.check_and_increment(a2, "delete_*", 30)
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_distinct_tools_independent():
    store = InMemoryRateLimitStore()
    aid = uuid4()
    for _ in range(5):
        await store.check_and_increment(aid, "delete_a", 5)
    decision = await store.check_and_increment(aid, "delete_b", 5)
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_fail_safe_when_unhealthy():
    store = InMemoryRateLimitStore()
    store._set_healthy(False)
    decision = await store.check_and_increment(uuid4(), "x", 30)
    assert decision.allowed is False
    assert decision.reason == "store_unavailable"


@pytest.mark.asyncio
async def test_health_check():
    store = InMemoryRateLimitStore()
    assert await store.health_check() is True
    store._set_healthy(False)
    assert await store.health_check() is False


@pytest.mark.asyncio
async def test_bounded_lru_evicts_oldest():
    store = InMemoryRateLimitStore(max_keys=5)
    for i in range(10):
        aid = uuid4()
        await store.check_and_increment(aid, f"tool_{i}", 30)
    # Le bucket bounded ne doit pas dépasser 5
    assert len(store._buckets) <= 5


@pytest.mark.asyncio
async def test_concurrent_safe():
    """Vérifie que le lock interne sérialise correctement."""
    store = InMemoryRateLimitStore()
    aid = uuid4()
    coros = [
        store.check_and_increment(aid, "create_x", 10) for _ in range(10)
    ]
    results = await asyncio.gather(*coros)
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 10


def test_resolve_limit_prefix_match():
    limits = _default_limits()
    assert resolve_limit("update_company_profile", limits) == 30
    assert resolve_limit("create_project", limits) == 10
    assert resolve_limit("delete_project", limits) == 5
    assert resolve_limit("generate_attestation", limits) == 5
    # Catch-all
    assert resolve_limit("recall_history", limits) == 30


def test_resolve_limit_unknown_prefix_falls_back_to_catchall():
    assert resolve_limit("foobar_x", _default_limits()) == 30
