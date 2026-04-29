"""F31 — Modèle SQLAlchemy ``action_step`` (étape d'un plan)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

# Réutilisation des types PG créés par la migration 0021
# create_type=False : SQLAlchemy ne tente pas de re-créer l'enum.
_CategoryPg = ENUM(
    "esg",
    "carbone",
    "credit",
    "candidature",
    name="action_step_category",
    create_type=False,
)
_PriorityPg = ENUM(
    "haute",
    "moyenne",
    "basse",
    name="action_step_priority",
    create_type=False,
)
_StatusPg = ENUM(
    "todo",
    "doing",
    "done",
    "postponed",
    name="action_step_status",
    create_type=False,
)


class ActionStep(Base):
    __tablename__ = "action_step"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("action_plan.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(_CategoryPg, nullable=False)
    priority: Mapped[str] = mapped_column(_PriorityPg, nullable=False)
    horizon_at: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(_StatusPg, nullable=False, default="todo")
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    indicateur_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indicateur.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    plan = relationship("ActionPlan", back_populates="steps")

    __table_args__ = (
        CheckConstraint(
            "char_length(title) BETWEEN 3 AND 200",
            name="chk_action_step_title_len",
        ),
    )
