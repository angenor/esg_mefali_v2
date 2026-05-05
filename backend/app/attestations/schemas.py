"""F30 - Pydantic schemas pour les endpoints attestation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    """Body de POST /me/attestations."""

    model_config = ConfigDict(extra="forbid")

    scores_to_include: list[str] = Field(min_length=1, max_length=20)
    valid_for_months: Literal[3, 6, 12] = 6


class RevokeRequest(BaseModel):
    """Body de POST /me/attestations/{id}/revoke et /admin/attestations/{id}/revoke."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)


class AttestationOut(BaseModel):
    """Reponse des endpoints PME."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    public_id: uuid.UUID
    status: Literal["active", "expired", "revoked"]
    generated_at: datetime
    valid_until: datetime
    revoked_at: datetime | None = None
    scores_inclus: dict[str, Any]
    referentiels_versions: dict[str, str]
    signature_ed25519: str
    pubkey_fingerprint: str
    hash_document: str
    download_url: str
    verify_url: str


class PublicIndicator(BaseModel):
    """F49 T009 — KPI exposé publiquement avec libellé bilingue optionnel."""

    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    label_en: str | None = None
    value: Any
    unit: str | None = None
    source_id: str | None = None


class PublicVerification(BaseModel):
    """Payload de la page publique /verify/{public_id}/json."""

    model_config = ConfigDict(extra="forbid")

    public_id: uuid.UUID
    status: Literal["active", "expired", "revoked"]
    entreprise_name: str
    generated_at: datetime
    valid_until: datetime
    revoked_at: datetime | None = None
    revoke_reason: str | None = None
    scores: dict[str, Any]
    referentiels_versions: dict[str, str]
    hash_document: str
    signature_ed25519: str
    pubkey_fingerprint: str
    download_url: str
    # F49 T009 — liste structurée des KPI (avec label_en optionnel) ;
    # complémentaire à `scores` qui reste un dict K/V brut pour rétrocompat.
    indicators: list[PublicIndicator] = []


class PubkeyOut(BaseModel):
    """Reponse de /verify/_pubkey."""

    model_config = ConfigDict(extra="forbid")

    pubkey_hex: str
    pubkey_fingerprint: str
    algorithm: Literal["ed25519"] = "ed25519"
