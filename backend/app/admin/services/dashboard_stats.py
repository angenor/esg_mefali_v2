"""F10 — Dashboard stats cache (T047, partial).

Provides a 60s in-process TTL cache. Aggregation queries are DEFERRED
to the full US5 implementation; only the cache primitive lives here for
now (so the invalidation hook can be wired by US4 revoke flow).
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any

from cachetools import TTLCache

_LOCK = threading.RLock()
_TTL = int(os.environ.get("ADMIN_DASHBOARD_CACHE_TTL", "60"))
_CACHE: TTLCache[str, Any] = TTLCache(maxsize=64, ttl=_TTL)


def get_or_compute(key: str, compute: Callable[[], Any]) -> Any:
    """Return cached value or compute + store it."""
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
        value = compute()
        _CACHE[key] = value
        return value


def invalidate(key: str | None = None) -> None:
    """Clear ``key`` (or the whole cache when ``None``)."""
    with _LOCK:
        if key is None:
            _CACHE.clear()
        else:
            _CACHE.pop(key, None)


def cache_size() -> int:
    """Diagnostic — current cache cardinality."""
    with _LOCK:
        return len(_CACHE)
