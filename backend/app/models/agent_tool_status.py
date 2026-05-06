"""F58 — Modèle ORM ``AgentToolStatus``.

Mappe la table ``agent_tool_status`` (kill-switch admin global) créée par
la migration 0037. Cette table est volontairement GLOBALE (pas de
``account_id``) car elle pilote le sélecteur de tools côté plateforme. Accès
admin uniquement (404 silencieux pour non-admin, P2 convention).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class AgentToolStatus(Base):
    """État d'activation d'un tool agent."""

    __tablename__ = "agent_tool_status"

    tool_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disabled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["AgentToolStatus"]
