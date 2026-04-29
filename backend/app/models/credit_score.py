"""F29 - Modele SQLAlchemy ``credit_score`` (append-only)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, SmallInteger
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class CreditScore(Base):
    """Score credit calcule pour une entreprise a un instant donne."""

    __tablename__ = "credit_score"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    entreprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    solvabilite: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    impact_vert: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    combine: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    facteurs: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    methodologie_version: Mapped[int] = mapped_column(Integer, nullable=False)
    coherence_warning: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
