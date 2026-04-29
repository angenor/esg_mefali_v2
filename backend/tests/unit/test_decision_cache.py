"""F03 US3 — Tests cache TTL des décisions middleware."""

from __future__ import annotations

import time

import pytest

from app.services.llm_validation import decision_cache


@pytest.fixture(autouse=True)
def _clean():
    decision_cache.clear()
    yield
    decision_cache.clear()


@pytest.mark.unit
def test_make_key_stable_sort_independent():
    a = decision_cache.make_key(
        message="x", cited_ids=["b", "a"], max_status_version=3
    )
    b = decision_cache.make_key(
        message="x", cited_ids=["a", "b"], max_status_version=3
    )
    assert a == b


@pytest.mark.unit
def test_make_key_changes_with_status_version():
    a = decision_cache.make_key(message="x", cited_ids=["a"], max_status_version=1)
    b = decision_cache.make_key(message="x", cited_ids=["a"], max_status_version=2)
    assert a != b


@pytest.mark.unit
def test_put_and_get_returns_same_value():
    k = decision_cache.make_key(message="m", cited_ids=[], max_status_version=0)
    decision_cache.put(k, "OK")
    assert decision_cache.get(k) == "OK"
    assert decision_cache.size() == 1


@pytest.mark.unit
def test_get_miss_returns_none():
    k = decision_cache.make_key(message="zzz", cited_ids=[], max_status_version=0)
    assert decision_cache.get(k) is None


@pytest.mark.unit
def test_clear_invalidates_all():
    k1 = decision_cache.make_key(message="a", cited_ids=[], max_status_version=0)
    k2 = decision_cache.make_key(message="b", cited_ids=[], max_status_version=0)
    decision_cache.put(k1, 1)
    decision_cache.put(k2, 2)
    decision_cache.clear()
    assert decision_cache.get(k1) is None
    assert decision_cache.get(k2) is None


@pytest.mark.unit
def test_invalidation_via_status_version_bump():
    """Bump du status_version => clé différente => miss."""
    k_v1 = decision_cache.make_key(
        message="m", cited_ids=["a"], max_status_version=1
    )
    decision_cache.put(k_v1, "old")
    k_v2 = decision_cache.make_key(
        message="m", cited_ids=["a"], max_status_version=2
    )
    assert decision_cache.get(k_v2) is None


@pytest.mark.unit
def test_ttl_expiration_short_window(monkeypatch):
    """Vérifie qu'on peut configurer un TTL court via patch (sanity)."""
    from cachetools import TTLCache

    short = TTLCache(maxsize=10, ttl=0.05)
    monkeypatch.setattr(decision_cache, "_decision_cache", short)
    decision_cache.put("k", "v")
    assert decision_cache.get("k") == "v"
    time.sleep(0.1)
    assert decision_cache.get("k") is None
