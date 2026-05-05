"""F52 — Modèle SQLAlchemy ``extension_ping``.

Heartbeat de l'extension Chrome (UPSERT par user). Consommé par US5 pour
afficher le statut "Extension détectée" dans `/parametres`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ExtensionPing(Base):
    __tablename__ = "extension_ping"

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
        unique=True,
    )
    extension_version: Mapped[str] = mapped_column(String, nullable=False)
    user_agent_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    last_ping_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
