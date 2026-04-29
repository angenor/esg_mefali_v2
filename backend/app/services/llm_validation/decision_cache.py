"""F03 US3 — Cache TTL des décisions du middleware anti-hallucination.

- TTLCache(maxsize=10000, ttl=300) — 5 min.
- Clé : sha256(message_text + sorted(cited_ids) + max(status_versions)).
- Invalidation explicite par bump du ``status_version`` (passé dans la clé).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from cachetools import TTLCache

CACHE_MAXSIZE = 10_000
CACHE_TTL_SECONDS = 300

# Cache process-local. Acceptable pour un déploiement single-instance ; la clé
# inclut status_version donc une invalidation se fait par bump SQL.
_decision_cache: TTLCache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL_SECONDS)


def make_key(
    *,
    message: str,
    cited_ids: Iterable[str],
    max_status_version: int,
) -> str:
    """Construit la clé sha256 stable du cache."""
    sorted_ids = sorted(str(i) for i in cited_ids)
    raw = "|".join(
        [message, ",".join(sorted_ids), str(max_status_version)]
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get(key: str):
    return _decision_cache.get(key)


def put(key: str, value) -> None:
    _decision_cache[key] = value


def clear() -> None:
    """Helper de test : vide le cache."""
    _decision_cache.clear()


def size() -> int:
    return len(_decision_cache)
