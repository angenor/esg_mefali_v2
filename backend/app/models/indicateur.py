"""F09 — modèle SQLAlchemy ``indicateur`` (PIVOT, Module 0.7)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Indicateur(Base):
    __tablename__ = "indicateur"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pillar: Mapped[str] = mapped_column(CHAR(11), nullable=False)
    unite: Mapped[str] = mapped_column(Text, nullable=False, default="")
    value_type: Mapped[str] = mapped_column(Text, nullable=False, default="numeric")
    enum_values: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    etag: Mapped[str] = mapped_column(Text, nullable=False, default="")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    logical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account_user.id"), nullable=True
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account_user.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint("code ~ '^[A-Z][A-Z0-9_]*$'", name="indicateur_code_format"),
    )
