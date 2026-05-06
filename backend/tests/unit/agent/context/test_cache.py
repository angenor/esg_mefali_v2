"""F54 / T033 — Tests unitaires du cache LRU+TTL (FR-007).

Couvre :
- set/get basique.
- TTL expiration.
- Eviction LRU au-delà de maxsize.
- Invalidation par account_id (cross-tenant safety).
- Clé contient account_id (P2 — pas de collision A↔B).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.agent.context.cache import (
    DEFAULT_MAXSIZE,
    DEFAULT_TTL_SECONDS,
    TTLCache,
    get_business_context_cache,
    invalidate_business_context,
    reset_business_context_cache,
)
from app.agent.context.models import (
    SCHEMA_VERSION,
    BusinessContext,
)


def _make_business_context(account_id) -> BusinessContext:
    return BusinessContext(
        account_id=account_id,
        user_id=uuid4(),
        user_role="pme",
        loaded_at=datetime.now(UTC),
    )


@pytest.mark.unit
class TestTTLCacheBasic:
    def test_set_get_roundtrip(self) -> None:
        cache: TTLCache[BusinessContext] = TTLCache(maxsize=4, ttl_seconds=60)
        aid = uuid4()
        ctx = _make_business_context(aid)
        cache.set(aid, SCHEMA_VERSION, ctx)
        assert cache.get(aid, SCHEMA_VERSION) is ctx

    def test_get_miss_returns_none(self) -> None:
        cache: TTLCache[BusinessContext] = TTLCache(maxsize=4, ttl_seconds=60)
        assert cache.get(uuid4(), SCHEMA_VERSION) is None

    def test_set_overwrites(self) -> None:
        cache: TTLCache[BusinessContext] = TTLCache(maxsize=4, ttl_seconds=60)
        aid = uuid4()
        c1 = _make_business_context(aid)
        c2 = _make_business_context(aid)
        cache.set(aid, SCHEMA_VERSION, c1)
        cache.set(aid, SCHEMA_VERSION, c2)
        assert cache.get(aid, SCHEMA_VERSION) is c2

    def test_invalid_maxsize_rejected(self) -> None:
        with pytest.raises(ValueError):
            TTLCache(maxsize=0, ttl_seconds=60)

    def test_invalid_ttl_rejected(self) -> None:
        with pytest.raises(ValueError):
            TTLCache(maxsize=4, ttl_seconds=0)


@pytest.mark.unit
class TestTTLCacheExpiration:
    def test_ttl_expires(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cache: TTLCache[BusinessContext] = TTLCache(maxsize=4, ttl_seconds=2)
        aid = uuid4()
        ctx = _make_business_context(aid)

        # Insert at t=100.0
        clock = [100.0]

        def _now() -> float:
            return clock[0]

        monkeypatch.setattr("app.agent.context.cache.time.monotonic", _now)
        cache.set(aid, SCHEMA_VERSION, ctx)
        assert cache.get(aid, SCHEMA_VERSION) is ctx

        # t=101.0 → encore dans la fenêtre.
        clock[0] = 101.0
        assert cache.get(aid, SCHEMA_VERSION) is ctx

        # t=103.0 → expiré (>2s).
        clock[0] = 103.0
        assert cache.get(aid, SCHEMA_VERSION) is None


@pytest.mark.unit
class TestTTLCacheLRU:
    def test_eviction_when_full(self) -> None:
        cache: TTLCache[BusinessContext] = TTLCache(maxsize=2, ttl_seconds=60)
        a, b, c = uuid4(), uuid4(), uuid4()
        cache.set(a, SCHEMA_VERSION, _make_business_context(a))
        cache.set(b, SCHEMA_VERSION, _make_business_context(b))
        # Lecture de a → MRU.
        cache.get(a, SCHEMA_VERSION)
        # Insère c → b doit être évincé (LRU).
        cache.set(c, SCHEMA_VERSION, _make_business_context(c))
        assert cache.get(a, SCHEMA_VERSION) is not None
        assert cache.get(b, SCHEMA_VERSION) is None
        assert cache.get(c, SCHEMA_VERSION) is not None


@pytest.mark.unit
class TestTTLCacheCrossTenantIsolation:
    """NFR-003 — la clé doit inclure account_id, jamais de collision A↔B."""

    def test_two_accounts_isolated(self) -> None:
        cache: TTLCache[BusinessContext] = TTLCache(maxsize=4, ttl_seconds=60)
        a = uuid4()
        b = uuid4()
        ctx_a = _make_business_context(a)
        ctx_b = _make_business_context(b)
        cache.set(a, SCHEMA_VERSION, ctx_a)
        cache.set(b, SCHEMA_VERSION, ctx_b)
        # A et B chacun voit son propre contexte.
        assert cache.get(a, SCHEMA_VERSION).account_id == a
        assert cache.get(b, SCHEMA_VERSION).account_id == b

    def test_invalidate_only_targets_one_account(self) -> None:
        cache: TTLCache[BusinessContext] = TTLCache(maxsize=4, ttl_seconds=60)
        a, b = uuid4(), uuid4()
        cache.set(a, SCHEMA_VERSION, _make_business_context(a))
        cache.set(b, SCHEMA_VERSION, _make_business_context(b))
        cache.invalidate(a)
        assert cache.get(a, SCHEMA_VERSION) is None
        assert cache.get(b, SCHEMA_VERSION) is not None

    def test_invalidate_drops_all_schema_versions(self) -> None:
        cache: TTLCache[BusinessContext] = TTLCache(maxsize=8, ttl_seconds=60)
        a = uuid4()
        cache.set(a, 1, _make_business_context(a))
        cache.set(a, 2, _make_business_context(a))
        n = cache.invalidate(a)
        assert n == 2
        assert cache.get(a, 1) is None
        assert cache.get(a, 2) is None


@pytest.mark.unit
class TestSingleton:
    def test_singleton_returns_same_instance(self) -> None:
        c1 = get_business_context_cache()
        c2 = get_business_context_cache()
        assert c1 is c2

    def test_invalidate_through_singleton(self) -> None:
        reset_business_context_cache()
        cache = get_business_context_cache()
        a = uuid4()
        cache.set(a, SCHEMA_VERSION, _make_business_context(a))
        invalidate_business_context(a)
        assert cache.get(a, SCHEMA_VERSION) is None


@pytest.mark.unit
class TestDefaults:
    def test_defaults(self) -> None:
        assert DEFAULT_TTL_SECONDS == 60
        assert DEFAULT_MAXSIZE >= 100
