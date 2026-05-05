"""F52 — Broker mémoire fan-out d'événements de notifications par compte.

Producteur : ``app/notifications/service.py`` lors de mark-all-read /
mark-read / création. Consommateur : ``app/notifications/stream.py`` (SSE).

Out-of-process scaling reste hors-scope MVP ; un Redis Pub/Sub pourra remplacer
ce broker quand on déploiera plusieurs workers (cf. research.md R8).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class NotificationsBroker:
    """Broker en mémoire ; les souscripteurs reçoivent les events de leur compte."""

    def __init__(self) -> None:
        self._subscribers: dict[uuid.UUID, set[asyncio.Queue[dict[str, Any]]]] = (
            defaultdict(set)
        )

    def subscribe(self, *, account_id: uuid.UUID) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
        self._subscribers[account_id].add(queue)
        return queue

    def unsubscribe(
        self, account_id: uuid.UUID, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        self._subscribers[account_id].discard(queue)
        if not self._subscribers[account_id]:
            self._subscribers.pop(account_id, None)

    def publish(
        self,
        *,
        account_id: uuid.UUID,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Publie ``{event, data}`` à tous les abonnés du compte (best-effort).

        Si une queue est pleine on drop l'event pour ce souscripteur sans
        bloquer le producteur (back-pressure : les SSE lents perdent des events
        plutôt que de bloquer la mutation métier).
        """
        envelope = {"event": event, "data": data}
        for queue in list(self._subscribers.get(account_id, ())):
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                logger.warning(
                    "notifications.broker: queue full for account=%s event=%s — drop",
                    account_id,
                    event,
                )


notifications_broker = NotificationsBroker()
