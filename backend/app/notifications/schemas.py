"""F34 — Schémas Pydantic pour les notifications PME."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

NotificationKind = Literal[
    "deadline_j_minus_30",
    "deadline_j_minus_7",
    "deadline_j_minus_1",
    "candidature_inactive",
    "offre_recommandee",
]

VALID_NOTIFICATION_KINDS: frozenset[str] = frozenset(
    {
        "deadline_j_minus_30",
        "deadline_j_minus_7",
        "deadline_j_minus_1",
        "candidature_inactive",
        "offre_recommandee",
    }
)


class NotificationOut(BaseModel):
    """Forme de sortie d'une notification (lecture)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: NotificationKind
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    payload_json: Any | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationListQuery(BaseModel):
    """Validation des query params pour ``GET /me/notifications``."""

    unread: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class NotificationReadOut(BaseModel):
    """Forme de sortie de ``PATCH /me/notifications/{id}/read``."""

    id: uuid.UUID
    read_at: datetime
