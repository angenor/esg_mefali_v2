"""F38 T056 — Stub SSE keepalive `/me/events`.

Émet un événement ``ping`` toutes les 30 secondes pour maintenir la connexion
ouverte. Le shell front (F38) ignore le payload : seul l'établissement de la
connexion compte. F41 enrichira le générateur avec les événements métier
(`notification.created`, etc.).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user
from app.models.account_user import AccountUser

router = APIRouter(prefix="/me", tags=["notifications-stream"])

_PING_INTERVAL_SECONDS = 30


@router.get("/events")
async def stream_events(
    user: Annotated[AccountUser, Depends(get_current_user)],
) -> EventSourceResponse:
    """Stream SSE keepalive — voir contracts/sse-events.md."""

    async def gen() -> AsyncIterator[dict[str, str]]:
        while True:
            yield {
                "event": "ping",
                "data": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
            await asyncio.sleep(_PING_INTERVAL_SECONDS)

    return EventSourceResponse(gen())
