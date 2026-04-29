"""F27 - Pydantic schemas pour le simulateur de financement.

Tous les schemas sont immutables (frozen=True) et stricts (extra=forbid).
Coherence : Money type (F05), sources tracees (F03).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.currencies import Currency
from app.schemas.money import Money

Instrument = Literal["subvention", "pret", "equity", "blending", "unknown"]


class SimulationHypotheses(BaseModel):
    """Hypotheses configurables d'une simulation (override des defauts catalog)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    taux_interet_pct: Decimal | None = Field(default=None, ge=0, le=100)
    duree_mois: int | None = Field(default=None, ge=1, le=600)
    garantie_pct: Decimal | None = Field(default=None, ge=0, le=200)


class SimulationRequest(BaseModel):
    """Body POST /me/simulations."""

    model_config = ConfigDict(extra="forbid")

    projet_id: UUID
    offre_id: UUID
    hypotheses: SimulationHypotheses | None = None


class ComparatorRequest(BaseModel):
    """Body POST /me/simulations/comparator."""

    model_config = ConfigDict(extra="forbid")

    projet_id: UUID
    offre_ids: list[UUID] = Field(min_length=2, max_length=5)
    hypotheses: SimulationHypotheses | None = None


class SimulationResult(BaseModel):
    """Resultat d'une simulation pour une Offre donnee."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    projet_id: UUID
    offre_id: UUID
    instrument: Instrument
    montant_eligible: Money
    frais_dossier: Money | None = None
    marge_intermediaire: Money | None = None
    garantie_exigee: Money | None = None  # informative, hors cout_total
    interets_cumules: Money | None = None
    cout_total: Money
    cout_total_pct: Decimal
    duree_mois: int | None = None
    taux_interet_pct: Decimal | None = None
    devise_emprunt: Currency
    equivalent_xof: Money | None = None
    change_risk: bool = False
    dilution_warning: bool = False
    unsourced: bool = False
    unknown_fields: list[str] = Field(default_factory=list)
    source_ids: list[UUID] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_serializer("cout_total_pct")
    def _serialize_pct(self, v: Decimal) -> str:
        return format(v, "f")

    @field_serializer("taux_interet_pct")
    def _serialize_taux(self, v: Decimal | None) -> str | None:
        return None if v is None else format(v, "f")


class ComparatorResult(BaseModel):
    """Resultat du comparateur multi-offres (rows tries par cout_total asc)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    projet_id: UUID
    rows: list[SimulationResult]
