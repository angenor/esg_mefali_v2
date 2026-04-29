"""F13 — In-process EventBus (asyncio per-account fan-out).

Cohérent avec ``app.entreprise.events`` (même style), mais générique (clé =
account_id, payload = dict). Conçu pour ``/me/events`` (FR-005, FR-027).

Multi-tenant strict : un publish sur account A ne diffuse jamais à account B
(filtrage server-side au niveau du dictionnaire ``_subscribers``).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
_lock = asyncio.Lock()


def _key(account_id: UUID | str) -> str:
    return str(account_id)


async def publish(account_id: UUID | str, payload: dict[str, Any]) -> int:
    """Diffuse ``payload`` à tous les abonnés du compte. Renvoie le nombre
    d'abonnés effectivement notifiés."""
    aid = _key(account_id)
    async with _lock:
        queues = list(_subscribers.get(aid, set()))
    msg = json.dumps(payload, default=str)
    delivered = 0
    for q in queues:
        try:
            q.put_nowait(msg)
            delivered += 1
        except asyncio.QueueFull:
            logger.warning("chat event_bus queue full for account=%s", aid)
    return delivered


async def subscribe(account_id: UUID | str) -> AsyncIterator[str]:
    """Itère sur les messages JSON pour ce compte, avec keepalive 15s."""
    aid = _key(account_id)
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
    async with _lock:
        _subscribers[aid].add(q)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=15.0)
                yield msg
            except TimeoutError:
                yield ":keepalive\n\n"
    finally:
        async with _lock:
            _subscribers.get(aid, set()).discard(q)


def subscriber_count(account_id: UUID | str) -> int:
    return len(_subscribers.get(_key(account_id), set()))
