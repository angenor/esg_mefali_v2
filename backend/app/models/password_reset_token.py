"""Modèle PasswordResetToken (nouvelle table F02)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

_TS_TZ = DateTime(timezone=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(_TS_TZ, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(_TS_TZ, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(_TS_TZ, nullable=True)
