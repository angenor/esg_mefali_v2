"""F12 - Pub/sub in-process pour evenements projet (mirror entreprise.events).

Un canal par account_id (asyncio.Queue par abonne).
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


async def publish(account_id: UUID | str, payload: dict[str, Any]) -> int:
    aid = str(account_id)
    async with _lock:
        queues = list(_subscribers.get(aid, set()))
    msg = json.dumps(payload, default=str)
    delivered = 0
    for q in queues:
        try:
            q.put_nowait(msg)
            delivered += 1
        except asyncio.QueueFull:
            logger.warning("projet events queue full for account=%s", aid)
    return delivered


def publish_sync(account_id: UUID | str, payload: dict[str, Any]) -> None:
    """Variante non-async best-effort."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(publish(account_id, payload))
            return
    except RuntimeError:
        pass
    logger.debug("publish_sync: no running loop, projet event dropped account=%s", account_id)


async def subscribe(account_id: UUID | str) -> AsyncIterator[str]:
    aid = str(account_id)
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
    return len(_subscribers.get(str(account_id), set()))
