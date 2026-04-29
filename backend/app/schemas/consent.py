"""F05 T030 — Consent Pydantic schemas + ConsentKind enum."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ConsentKind(StrEnum):
    """Cinq consentements optionnels (cf. data-model.md §enum)."""

    MOBILE_MONEY = "mobile_money"
    EXPLOITATION_PHOTOS = "exploitation_photos"
    PUBLIC_ATTESTATION = "public_attestation"
    LONG_HISTORY = "long_history"
    MARKETING = "marketing"


class ConsentOut(BaseModel):
    """Vue API d'un consentement utilisateur."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    consent_kind: ConsentKind
    given: bool
    given_at: datetime | None = None
    withdrawn_at: datetime | None = None
    source_of_change: str
    updated_at: datetime


class ConsentToggleIn(BaseModel):
    """Payload du POST /me/consentements/{kind}."""

    model_config = ConfigDict(extra="forbid")

    given: bool


class ConsentRequiredError(BaseModel):
    """Body 403 d'un endpoint protégé par ``RequiresConsent``."""

    error: str = "consent_required"
    kind: ConsentKind
