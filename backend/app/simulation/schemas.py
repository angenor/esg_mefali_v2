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

TypeInvestissement = Literal[
    "renouvelable_solaire",
    "renouvelable_eolien",
    "efficacite_energetique",
    "agriculture_durable",
    "mobilite_electrique",
    "autre",
]


class SimulationHypotheses(BaseModel):
    """Hypotheses configurables d'une simulation (override des defauts catalog).

    Champs F27 (override catalog) : taux_interet_pct, duree_mois, garantie_pct.
    Champs F51 (mode pedagogique sans projet/offre) : montant, type_investissement,
    part_subvention_pct.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    taux_interet_pct: Decimal | None = Field(default=None, ge=0, le=100)
    duree_mois: int | None = Field(default=None, ge=1, le=600)
    garantie_pct: Decimal | None = Field(default=None, ge=0, le=200)
    montant: Money | None = None
    type_investissement: TypeInvestissement | None = None
    part_subvention_pct: Decimal | None = Field(default=None, ge=0, le=100)


class SimulationRequest(BaseModel):
    """Body POST /me/simulations.

    `projet_id` et `offre_id` peuvent etre `None` (mode pedagogique F51) :
    le calcul est alors purement base sur `hypotheses`.
    """

    model_config = ConfigDict(extra="forbid")

    projet_id: UUID | None = None
    offre_id: UUID | None = None
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


# ---------- F51 — Mode pedagogique (preview) ----------


class MensualiteEntry(BaseModel):
    """Une mensualite du tableau d'amortissement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mois: int = Field(ge=1)
    amount: str
    currency: Currency


class DecompositionPct(BaseModel):
    """Repartition % du financement entre principal, interets et subvention."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    principal: float
    interets: float
    subvention: float


class FormulaRef(BaseModel):
    """Reference a une formule du catalog (versionnee, P4)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    formula_id: str
    version: str


class SimulationResults(BaseModel):
    """Reponse de POST /me/simulations en mode pedagogique F51.

    Shape conforme au contrat `simulateur_api_extensions.md` § 1 et au type
    frontend `SimulationResults` (frontend/app/types/simulateur.ts).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    mensualites: list[MensualiteEntry]
    cout_total: Money
    economie_estimee: Money
    co2_evite_t: str
    decomposition_pct: DecompositionPct
    formula_refs: list[FormulaRef] = Field(default_factory=list)
    computed_at: str | None = None


# ---------- F51 — Save & history ----------


class SimulationSaveIn(BaseModel):
    """Body POST /me/simulations/save."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=120)
    projet_id: UUID | None = None
    offre_id: UUID | None = None
    hypotheses: dict[str, object] = Field(default_factory=dict)
    results: dict[str, object] = Field(default_factory=dict)


class SimulationSavedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    label: str
    projet_id: UUID | None = None
    offre_id: UUID | None = None
    hypotheses: dict[str, object]
    results_summary: dict[str, object]
    created_at: str


class SimulationSavedListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SimulationSavedItem]
    count: int
    next_cursor: str | None = None


class SimulationSavedDetailOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    label: str
    projet_id: UUID | None = None
    offre_id: UUID | None = None
    hypotheses: dict[str, object]
    results: dict[str, object]
    created_at: str


class SimulationSaveOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    label: str
    created_at: str
