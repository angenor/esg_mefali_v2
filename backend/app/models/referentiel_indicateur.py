"""F09 — modèle SQLAlchemy jonction ``referentiel_indicateur``."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ReferentielIndicateur(Base):
    __tablename__ = "referentiel_indicateur"

    referentiel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("referentiel.id", ondelete="CASCADE"), primary_key=True
    )
    indicateur_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("indicateur.id", ondelete="RESTRICT"), primary_key=True
    )
    poids: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    seuil_min: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    seuil_max: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source.id"), nullable=False
    )
