"""F55 — Rate limiter pluggable (FR-010, NFR-007).

Interface ``RateLimitStore`` (Protocol) ; deux implémentations :
- ``InMemoryRateLimitStore`` : asyncio.Lock + bounded LRU 1000 keys, fenêtre
  glissante 60 s. Convient en dev single-worker.
- ``RedisRateLimitStore`` : stub Lua atomic INCR+EXPIRE pour prod multi-worker.

Sélection au boot via ``LLM_AGENT_RATE_LIMIT_BACKEND={memory,redis}``.

**Fail-safe NFR-007** : si le store est inaccessible, ``check_and_increment``
retourne ``RateLimitDecision(allowed=False, reason='store_unavailable')``.
Le dispatcher refusera la mutation (jamais fail-open).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.agent.state import RateLimitDecision

logger = logging.getLogger(__name__)


WINDOW_SECONDS = 60
MAX_BOUNDED_KEYS = 1000


class RateLimitStore(Protocol):
    """Contrat asyncio-safe d'un rate limiter (FR-010)."""

    async def check_and_increment(
        self,
        account_id: UUID,
        tool_name: str,
        limit_per_minute: int,
    ) -> RateLimitDecision: ...

    async def health_check(self) -> bool: ...


class InMemoryRateLimitStore:
    """Rate limiter in-memory à fenêtre glissante 60 s.

    Bounded LRU pour limiter la mémoire (max 1000 (account, tool) keys).
    """

    def __init__(self, *, max_keys: int = MAX_BOUNDED_KEYS) -> None:
        self._lock = asyncio.Lock()
        self._buckets: OrderedDict[tuple[UUID, str], list[float]] = OrderedDict()
        self._max_keys = max_keys
        self._healthy = True

    def _set_healthy(self, healthy: bool) -> None:
        # Hook pour les tests : permet de simuler un store down.
        self._healthy = healthy

    async def check_and_increment(
        self,
        account_id: UUID,
        tool_name: str,
        limit_per_minute: int,
    ) -> RateLimitDecision:
        if not self._healthy:
            return RateLimitDecision(
                allowed=False, remaining=0, reason="store_unavailable"
            )
        try:
            async with self._lock:
                now = time.monotonic()
                window_start = now - WINDOW_SECONDS

                key = (account_id, tool_name)
                if key in self._buckets:
                    self._buckets.move_to_end(key)
                bucket = self._buckets.get(key, [])

                # Purge entries plus vieilles que la fenêtre
                bucket = [t for t in bucket if t >= window_start]

                if len(bucket) >= limit_per_minute:
                    self._buckets[key] = bucket
                    reset_at = datetime.now(UTC) + timedelta(
                        seconds=WINDOW_SECONDS - (now - bucket[0])
                    )
                    return RateLimitDecision(
                        allowed=False,
                        remaining=0,
                        reset_at=reset_at,
                        reason="exceeded",
                    )

                bucket.append(now)
                self._buckets[key] = bucket

                # Bounded eviction (LRU)
                while len(self._buckets) > self._max_keys:
                    self._buckets.popitem(last=False)

                remaining = max(0, limit_per_minute - len(bucket))
                reset_at = datetime.now(UTC) + timedelta(seconds=WINDOW_SECONDS)
                return RateLimitDecision(
                    allowed=True,
                    remaining=remaining,
                    reset_at=reset_at,
                    reason="ok",
                )
        except Exception:  # pragma: no cover - defensive
            logger.exception("InMemoryRateLimitStore unexpected error")
            return RateLimitDecision(
                allowed=False, remaining=0, reason="store_unavailable"
            )

    async def health_check(self) -> bool:
        return self._healthy


class RedisRateLimitStore:
    """Stub Redis pour multi-worker prod (Lua atomic INCR+EXPIRE).

    L'implémentation complète sera livrée en F58. En dev / tests on utilise
    InMemory ; ce stub garantit le fail-safe (toujours unavailable) tant que
    Redis n'est pas connecté.
    """

    def __init__(self, *, redis_url: str | None = None) -> None:
        self._redis_url = redis_url
        self._client = None  # type: ignore[var-annotated]

    async def check_and_increment(
        self,
        account_id: UUID,
        tool_name: str,
        limit_per_minute: int,
    ) -> RateLimitDecision:
        del account_id, tool_name, limit_per_minute  # unused — stub
        return RateLimitDecision(
            allowed=False, remaining=0, reason="store_unavailable"
        )

    async def health_check(self) -> bool:
        return False


# --- Configuration des limites ---------------------------------------------


def _default_limits() -> dict[str, int]:
    """Limites par défaut FR-010.

    Sur préfixe : update_* 30/min, create_* 10/min, delete_* 5/min,
    generate_* 5/min. Catch-all 30/min.
    """
    return {
        "update_*": 30,
        "create_*": 10,
        "delete_*": 5,
        "generate_*": 5,
        "*": 30,
    }


def resolve_limit(tool_name: str, limits: dict[str, int]) -> int:
    """Résout la limite/min pour un tool donné via préfixes glob."""
    # Match préfixe le plus spécifique
    for pattern, value in limits.items():
        if pattern == "*":
            continue
        if pattern.endswith("*") and tool_name.startswith(pattern[:-1]):
            return int(value)
    return int(limits.get("*", 30))


# --- Singleton store -------------------------------------------------------

_RATE_STORE: RateLimitStore | None = None


def get_rate_store() -> RateLimitStore:
    """Retourne (lazy-init) le rate store sélectionné par config."""
    global _RATE_STORE
    if _RATE_STORE is None:
        from app.config import get_settings

        backend = getattr(get_settings(), "LLM_AGENT_RATE_LIMIT_BACKEND", "memory")
        if backend == "redis":
            _RATE_STORE = RedisRateLimitStore()
        else:
            _RATE_STORE = InMemoryRateLimitStore()
    return _RATE_STORE


def set_rate_store(store: RateLimitStore | None) -> None:
    """Réservé aux tests : remplace le singleton par un fake."""
    global _RATE_STORE
    _RATE_STORE = store


__all__ = [
    "InMemoryRateLimitStore",
    "RateLimitStore",
    "RedisRateLimitStore",
    "_default_limits",
    "get_rate_store",
    "resolve_limit",
    "set_rate_store",
]
