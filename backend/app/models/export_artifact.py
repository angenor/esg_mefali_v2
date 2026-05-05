"""F52 — Modèle SQLAlchemy ``export_artifact``.

Historique des exports/rapports générés (RGPD JSON, rapports PDF, attestations,
dossiers PDF). Lu par `/me/exports`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

ExportType = Literal["rgpd_full", "report_pdf", "attestation_pdf", "dossier_pdf"]
ExportStatus = Literal["pending", "ready", "expired", "failed"]
ExportFormat = Literal["pdf", "json"]
ExportDeliveredVia = Literal["inapp", "email"]


class ExportArtifact(Base):
    __tablename__ = "export_artifact"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        ENUM(
            "rgpd_full",
            "report_pdf",
            "attestation_pdf",
            "dossier_pdf",
            name="export_type",
            create_type=False,
        ),
        nullable=False,
    )
    format: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(
        ENUM(
            "pending",
            "ready",
            "expired",
            "failed",
            name="export_status",
            create_type=False,
        ),
        nullable=False,
        default="pending",
    )
    signed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_url_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_via: Mapped[str | None] = mapped_column(String, nullable=True)
