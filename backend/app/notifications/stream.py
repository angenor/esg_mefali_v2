"""F38 + F52 — Stream SSE ``/me/events`` et ``/me/notifications/stream``.

- Connexions abonnées au broker mémoire (cf. ``broker.py``) recevant les events
  ``notification.created``, ``notification.read``, ``notification.bulk_read``.
- Pings toutes les 30 secondes pour maintenir la connexion ouverte.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user
from app.models.account_user import AccountUser
from app.notifications.broker import notifications_broker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["notifications-stream"])

_PING_INTERVAL_SECONDS = 30


async def _stream_for_account(account_id) -> AsyncIterator[dict[str, str]]:
    """Générateur SSE qui multiplexe broker + ping keepalive."""
    queue = notifications_broker.subscribe(account_id=account_id)
    try:
        while True:
            try:
                envelope = await asyncio.wait_for(
                    queue.get(), timeout=_PING_INTERVAL_SECONDS
                )
            except asyncio.TimeoutError:
                yield {
                    "event": "ping",
                    "data": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                }
                continue
            yield {
                "event": envelope["event"],
                "data": json.dumps(envelope["data"], default=str),
            }
    finally:
        notifications_broker.unsubscribe(account_id, queue)


@router.get("/events")
async def stream_events(
    user: Annotated[AccountUser, Depends(get_current_user)],
) -> EventSourceResponse:
    """Stream SSE général (F38 keepalive + F52 events broker)."""
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account"},
        )
    return EventSourceResponse(_stream_for_account(user.account_id))


@router.get("/notifications/stream")
async def stream_notifications(
    user: Annotated[AccountUser, Depends(get_current_user)],
) -> EventSourceResponse:
    """Alias dédié ``/me/notifications/stream`` (cf. contracts F52)."""
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account"},
        )
    return EventSourceResponse(_stream_for_account(user.account_id))
