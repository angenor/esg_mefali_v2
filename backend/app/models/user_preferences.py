"""F42 — Modèle UserPreferences (table ``user_preferences``)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

OnboardingState = Literal["pending", "completed", "skipped", "dismissed"]
ONBOARDING_STATES: tuple[OnboardingState, ...] = (
    "pending",
    "completed",
    "skipped",
    "dismissed",
)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account.id", ondelete="CASCADE"),
        nullable=False,
    )
    onboarding_state: Mapped[str] = mapped_column(
        Enum(*ONBOARDING_STATES, name="onboarding_state", native_enum=True, create_type=False),
        nullable=False,
        default="pending",
    )
    onboarding_state_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
