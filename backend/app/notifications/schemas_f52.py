"""F52 — Schémas Pydantic v2 pour le centre des notifications étendu.

- ``NotificationListQueryF52`` : filtre `kind[]` + `from`/`to` + cursor.
- ``ReadAllRequest`` / ``ReadAllResponse`` : batch mark-all-read (SC-002).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.notifications.schemas import NotificationKind


class NotificationListQueryF52(BaseModel):
    """Query params étendus pour ``GET /me/notifications`` (US1)."""

    model_config = ConfigDict(extra="forbid")

    unread_only: bool = False
    kind: list[NotificationKind] = Field(default_factory=list)
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class ReadAllRequest(BaseModel):
    """Body de ``POST /me/notifications/read-all``.

    ``kinds`` optionnel ; absent → marquer toutes les non-lues.
    """

    model_config = ConfigDict(extra="forbid")

    kinds: list[NotificationKind] | None = None


class ReadAllResponse(BaseModel):
    """Réponse standard de mark-all-read."""

    model_config = ConfigDict(extra="forbid")

    updated_count: int = Field(ge=0)
    unread_count_after: int = Field(ge=0)
