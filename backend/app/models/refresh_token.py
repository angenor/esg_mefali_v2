"""Modèle RefreshToken (nouvelle table F02)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

_TS_TZ = DateTime(timezone=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    issued_at: Mapped[datetime] = mapped_column(_TS_TZ, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(_TS_TZ, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(_TS_TZ, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(_TS_TZ, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String, nullable=True)
