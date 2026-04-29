"""F30 - Modele SQLAlchemy ``attestation``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Attestation(Base):
    """Attestation verifiable emise par une PME."""

    __tablename__ = "attestation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    entreprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4
    )
    scores_inclus_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    referentiels_versions_json: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    signature_ed25519: Mapped[str] = mapped_column(String(256), nullable=False)
    pubkey_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    hash_document: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    generated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    revoked_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
