"""F54 / FR-007 — Cache LRU+TTL process-local pour BusinessContext.

**Pas de Redis** — un singleton process-local en mémoire suffit pour le MVP
(un seul worker FastAPI). La clé inclut systématiquement ``account_id``
pour garantir l'isolation cross-tenant (P2, NFR-003).

Stratégie d'invalidation **hybride** :

1. ``invalidate(account_id)`` appelé directement par les services qui mutent
   les données (entreprise, projets, candidatures, indicateurs, score,
   plan d'action) — c'est l'invalidation push instantanée.
2. TTL fallback de 60 secondes — couvre les cas où la mutation a oublié
   d'émettre. Un cache « hot » est valide ≤ 60 s même sans push.

Thread-safety : un :class:`threading.RLock` protège le dict interne (le
runner peut être multi-thread via Uvicorn workers).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


#: TTL fallback par défaut (FR-007).
DEFAULT_TTL_SECONDS: int = 60

#: Capacité LRU par défaut (≤ 100 PME concurrentes anticipées en MVP).
DEFAULT_MAXSIZE: int = 512


@dataclass
class _Entry[T]:
    value: T
    inserted_at_monotonic: float
    schema_version: int


class TTLCache[T]:
    """LRU+TTL minimal thread-safe (cachetools-like, sans dépendance externe).

    L'éviction LRU se fait sur ``__getitem__`` (le plus récemment lu remonte)
    via une stratégie OrderedDict émulée par un dict + cycle de réinsertion.
    """

    def __init__(
        self,
        *,
        maxsize: int = DEFAULT_MAXSIZE,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be >= 1")
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._store: dict[str, _Entry[T]] = {}
        self._lock = threading.RLock()

    def _key(self, account_id: UUID, schema_version: int) -> str:
        return f"{account_id}:{schema_version}"

    def get(self, account_id: UUID, schema_version: int) -> T | None:
        """Retourne la valeur cachée ou ``None``. Re-réinsère pour MRU LRU."""
        k = self._key(account_id, schema_version)
        with self._lock:
            entry = self._store.get(k)
            if entry is None:
                return None
            now = time.monotonic()
            if now - entry.inserted_at_monotonic > self._ttl:
                # TTL expiré → drop.
                self._store.pop(k, None)
                return None
            # MRU — réinsérer pour mettre en queue de l'OrderedDict émulé.
            self._store.pop(k, None)
            self._store[k] = entry
            return entry.value

    def set(self, account_id: UUID, schema_version: int, value: T) -> None:
        """Insère/écrase la valeur cachée. Évince LRU si plein."""
        k = self._key(account_id, schema_version)
        with self._lock:
            if k in self._store:
                self._store.pop(k, None)
            elif len(self._store) >= self._maxsize:
                # Évince le plus ancien (OrderedDict insertion order).
                try:
                    oldest_key = next(iter(self._store))
                    self._store.pop(oldest_key, None)
                except StopIteration:  # pragma: no cover - defensive
                    pass
            self._store[k] = _Entry(
                value=value,
                inserted_at_monotonic=time.monotonic(),
                schema_version=schema_version,
            )

    def invalidate(self, account_id: UUID) -> int:
        """Supprime toutes les entrées pour ``account_id`` (toute schema_version
        confondue). Renvoie le nombre d'entrées supprimées.
        """
        prefix = f"{account_id}:"
        with self._lock:
            keys_to_drop = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_drop:
                self._store.pop(k, None)
        if keys_to_drop:
            logger.debug("ctx_cache invalidate account=%s n=%d", account_id, len(keys_to_drop))
        return len(keys_to_drop)

    def clear(self) -> None:
        """Vide intégralement le cache."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:  # utilitaire diagnostique.
        with self._lock:
            return len(self._store)


# ---------------------------------------------------------------------------
# Singleton process-local
# ---------------------------------------------------------------------------

_business_context_cache: TTLCache | None = None
_singleton_lock = threading.Lock()


def get_business_context_cache() -> TTLCache:
    """Retourne le singleton :class:`TTLCache` du process pour BusinessContext.

    Ce singleton est utilisé par :mod:`app.agent.context.loader` (read-through)
    et invalidé via :func:`invalidate_business_context` par les mutations
    métier (US2 / SC-004).
    """
    global _business_context_cache
    if _business_context_cache is None:
        with _singleton_lock:
            if _business_context_cache is None:
                _business_context_cache = TTLCache(
                    maxsize=DEFAULT_MAXSIZE,
                    ttl_seconds=DEFAULT_TTL_SECONDS,
                )
    return _business_context_cache


def invalidate_business_context(account_id: UUID) -> int:
    """Invalide toutes les entrées caches pour ``account_id``.

    À appeler par les services qui mutent les données métier (entreprise,
    projets, candidatures, indicateurs, score, plan d'action) immédiatement
    après le commit DB. Conformément à P8 (sync bidirectionnel UI ↔ LLM),
    le tour suivant verra la nouvelle valeur (SC-004).
    """
    return get_business_context_cache().invalidate(account_id)


def reset_business_context_cache() -> None:
    """Helper test-only : reset complet du singleton."""
    global _business_context_cache
    with _singleton_lock:
        if _business_context_cache is not None:
            _business_context_cache.clear()


__all__ = [
    "DEFAULT_MAXSIZE",
    "DEFAULT_TTL_SECONDS",
    "TTLCache",
    "get_business_context_cache",
    "invalidate_business_context",
    "reset_business_context_cache",
]
