"""F02 — Rate limiting.

Deux modes :
- ``limiter`` (slowapi) : exposé pour compatibilité, mais le décorateur
  ``@limiter.limit(...)`` casse l'inférence du body Pydantic dans FastAPI.
- ``check_rate(request, scope, rate)`` : appel impératif depuis le handler.
  Compteur en mémoire (LIFO bucket par clé). Désactivable via
  ``DISABLE_RATE_LIMIT=1``.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _key_func(request: Request) -> str:
    """Retourne l'IP cliente, en respectant X-Forwarded-For si présent."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_key_func)

_buckets: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def _parse_rate(rate: str) -> tuple[int, float]:
    """Parse "5/minute" -> (5, 60.0). Supporte minute, hour, second, day."""
    n_str, _, period = rate.partition("/")
    n = int(n_str)
    p = period.strip().lower()
    seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(p, 60)
    return n, float(seconds)


def check_rate(request: Request, scope: str, rate: str) -> None:
    """Vérifie un rate-limit impératif. Lève 429 si dépassé.

    Désactivé en mode test si l'env ``DISABLE_RATE_LIMIT=1`` est positionné.
    """
    if os.environ.get("DISABLE_RATE_LIMIT") == "1":
        return
    n, period = _parse_rate(rate)
    key = f"{scope}:{_key_func(request)}"
    now = time.monotonic()
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < now - period:
            bucket.popleft()
        if len(bucket) >= n:
            raise HTTPException(
                status_code=429,
                detail={"code": "rate_limited", "message": "Trop de tentatives."},
            )
        bucket.append(now)
