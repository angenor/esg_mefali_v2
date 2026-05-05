"""F52 — Schémas Pydantic pour ``/me/parametres/*``.

Couvre :
- Préférences notifications (matrice kind × channel) → ``app/notifications``.
- Changement d'e-mail avec re-vérification (TTL 24 h).
- Sessions actives (refresh_tokens) + révocation individuelle.
- Demande de suppression de compte (workflow J+30).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

from app.notifications.schemas import NotificationKind

# ---------------------------------------------------------------------------
# Préférences notifications
# ---------------------------------------------------------------------------

NotificationChannel = Literal["email", "in_app"]


class NotificationPreferenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: NotificationKind
    channel: NotificationChannel
    enabled: bool


class NotificationPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updates: list[NotificationPreferenceItem] = Field(min_length=1, max_length=50)


class NotificationPreferencesOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NotificationPreferenceItem]


# ---------------------------------------------------------------------------
# Changement d'e-mail
# ---------------------------------------------------------------------------


class EmailChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_email: EmailStr
    current_password: SecretStr


class EmailChangeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_pending: EmailStr
    verification_sent_at: datetime


class EmailVerifyOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class SessionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    device_label: str
    ip_country: str | None = None
    user_agent_summary: str | None = None
    created_at: datetime
    last_seen_at: datetime
    is_current: bool


class SessionsListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SessionOut]


# ---------------------------------------------------------------------------
# Suppression compte (workflow J+30)
# ---------------------------------------------------------------------------


class AccountDeletionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_text: str = Field(min_length=1, max_length=255)
    reason_motif: str | None = Field(default=None, max_length=1024)


class AccountDeletionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: Literal["pending", "cancelled", "executed"]
    requested_at: datetime
    scheduled_for: datetime
    can_cancel: bool


class AccountDeletionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: AccountDeletionOut | None = None
