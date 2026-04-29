"""F28 - Modele SQLAlchemy ``carbon_footprint``."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class CarbonFootprint(Base):
    __tablename__ = "carbon_footprint"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    entreprise_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    source_data_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    total_tco2e: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    by_scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    breakdown_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    factor_versions_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
