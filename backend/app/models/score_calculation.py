"""F23 — Modèle SQLAlchemy ``score_calculation`` (append-only)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ScoreCalculation(Base):
    __tablename__ = "score_calculation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    referentiel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("referentiel.id"), nullable=False
    )
    referentiel_version: Mapped[int] = mapped_column(Integer, nullable=False)
    referentiel_code: Mapped[str] = mapped_column(Text, nullable=False)

    score_global: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    scores_by_pillar: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    details_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    coverage_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    computed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account_user.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('entreprise','projet')",
            name="chk_score_calc_entity_type",
        ),
        CheckConstraint(
            "score_global IS NULL OR (score_global >= 0 AND score_global <= 100)",
            name="chk_score_calc_score_range",
        ),
        CheckConstraint(
            "coverage_ratio IS NULL OR (coverage_ratio >= 0 AND coverage_ratio <= 1)",
            name="chk_score_calc_coverage_range",
        ),
    )
