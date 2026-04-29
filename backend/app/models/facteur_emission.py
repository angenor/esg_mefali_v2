"""F09 — modèle SQLAlchemy ``facteur_emission``."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, Date, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class FacteurEmission(Base):
    __tablename__ = "facteur_emission"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    valeur: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unite: Mapped[str] = mapped_column(Text, nullable=False)
    pays_iso2: Mapped[str | None] = mapped_column(CHAR(2), nullable=True)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    categorie: Mapped[str] = mapped_column(Text, nullable=False, default="autre")
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valid_from_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    etag: Mapped[str] = mapped_column(Text, nullable=False, default="")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    logical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
