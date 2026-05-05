"""F52 — Modèle SQLAlchemy ``account_deletion_request``.

Workflow J+30 : un row par compte (UNIQUE WHERE status='pending'). Transitions
``pending → cancelled`` (utilisateur) ou ``pending → executed`` (job de purge).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

DeletionStatus = Literal["pending", "cancelled", "executed"]


class AccountDeletionRequest(Base):
    __tablename__ = "account_deletion_request"

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
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        ENUM(
            "pending",
            "cancelled",
            "executed",
            name="deletion_status",
            create_type=False,
        ),
        nullable=False,
        default="pending",
    )
    reason_motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmation_text: Mapped[str] = mapped_column(String, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
