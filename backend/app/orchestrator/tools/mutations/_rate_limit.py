"""F17 — Décorateur ``@rate_limited`` (FR-010).

In-process token-bucket par user_id : 10 mutations LLM / 60 secondes glissantes.
Acceptable en MVP ; à remplacer par Redis post-MVP.

Caller : modules ``update_company_profile``, ``create_project``,
``update_project``, ``delete_project``.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from functools import wraps
from typing import Any

DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_MAX_PER_MIN = 10


class RateLimitExceeded(Exception):
    """Levée quand un user dépasse ``max_per_min`` mutations/minute."""

    def __init__(self, user_id: str, max_per_min: int) -> None:
        self.user_id = user_id
        self.max_per_min = max_per_min
        super().__init__(
            f"Rate limit exceeded for user {user_id}: max {max_per_min}/min"
        )


_state: dict[str, deque[float]] = {}
_lock = threading.Lock()


def _user_key(_args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Extrait le user_id d'une signature de tool handler."""
    user_id = kwargs.get("user_id")
    if user_id is not None:
        return str(user_id)
    return "_anonymous"


def reset_rate_limit_state() -> None:
    """Vide l'état du rate limiter (réservé aux tests)."""
    with _lock:
        _state.clear()


def rate_limited(
    *,
    max_per_min: int = DEFAULT_MAX_PER_MIN,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Décorateur factory.

    Le handler décoré DOIT recevoir ``user_id`` en kwarg. Lève
    ``RateLimitExceeded`` si le user a déjà déclenché ``max_per_min``
    mutations dans la fenêtre glissante.
    """

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _user_key(args, kwargs)
            now = time.monotonic()
            with _lock:
                bucket = _state.setdefault(key, deque())
                cutoff = now - window_seconds
                while bucket and bucket[0] < cutoff:
                    bucket.popleft()
                if len(bucket) >= max_per_min:
                    raise RateLimitExceeded(user_id=key, max_per_min=max_per_min)
                bucket.append(now)
            return fn(*args, **kwargs)

        return wrapper

    return decorate


__all__ = [
    "DEFAULT_MAX_PER_MIN",
    "DEFAULT_WINDOW_SECONDS",
    "RateLimitExceeded",
    "rate_limited",
    "reset_rate_limit_state",
]
