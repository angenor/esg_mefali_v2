"""F25 — Schémas DTO pour le matching projet <-> offre.

DTO immutables (`frozen=True`). Money typé via `app.schemas.money`.

F51 ajoute les schémas Pydantic ``OffreFilters``, ``OffreListItem``,
``OffreListOut`` et ``OffreDetailOut`` pour ``GET /me/offres`` et
``GET /me/offres/{id}``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.money import Money

OffreType = Literal["credit", "subvention", "garantie", "autre"]


@dataclass(frozen=True)
class CritereMatch:
    """Critère unitaire évalué (côté fonds OU intermédiaire)."""

    code: str
    label: str
    severity: str  # 'blocking' | 'warning'
    covered: bool
    source_id: UUID | None = None
    reason: str | None = None  # 'value_missing', 'out_of_range', etc.


@dataclass(frozen=True)
class OfferMatch:
    """Résultat compact d'un matching pour une offre."""

    offre_id: UUID
    fonds_id: UUID
    intermediaire_id: UUID | None
    fonds_score: float
    intermediaire_score: float
    score_global: float  # = min(fonds_score, intermediaire_score)
    libelle: str
    deadline_iso: str | None = None


@dataclass(frozen=True)
class MatchDetail:
    """Détail complet d'un match (US3)."""

    offre_id: UUID
    fonds_id: UUID
    intermediaire_id: UUID | None
    fonds_score: float
    intermediaire_score: float
    score_global: float
    criteres_couverts_fonds: list[CritereMatch] = field(default_factory=list)
    criteres_manquants_fonds: list[CritereMatch] = field(default_factory=list)
    criteres_couverts_intermediaire: list[CritereMatch] = field(default_factory=list)
    criteres_manquants_intermediaire: list[CritereMatch] = field(default_factory=list)
    documents_requis: list[str] = field(default_factory=list)
    frais_effectifs: Money | None = None
    delais_effectifs_jours: int | None = None


@dataclass(frozen=True)
class ComparatorRow:
    """Ligne du comparateur multi-intermédiaires (US4)."""

    offre_id: UUID
    intermediaire_id: UUID | None
    intermediaire_name: str
    fonds_score: float
    intermediaire_score: float
    score_global: float
    delais_effectifs_jours: int | None
    frais_effectifs: Money | None
    documents_count: int


# ----- F51 — catalogue listing & detail -----


class OffreFilters(BaseModel):
    """Filtres ``GET /me/offres`` (tous optionnels). Validation pre-query."""

    model_config = ConfigDict(extra="forbid")

    type: OffreType | None = None
    montant_min_eur: int | None = Field(default=None, ge=0)
    montant_max_eur: int | None = Field(default=None, ge=0)
    duree_min_mois: int | None = Field(default=None, ge=1, le=240)
    duree_max_mois: int | None = Field(default=None, ge=1, le=240)
    intermediaire_id: UUID | None = None
    secteur: str | None = Field(default=None, max_length=64)
    q: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=20, ge=1, le=50)

    @model_validator(mode="after")
    def _check_ranges(self) -> OffreFilters:
        if (
            self.montant_min_eur is not None
            and self.montant_max_eur is not None
            and self.montant_min_eur > self.montant_max_eur
        ):
            raise ValueError("montant_min_eur > montant_max_eur")
        if (
            self.duree_min_mois is not None
            and self.duree_max_mois is not None
            and self.duree_min_mois > self.duree_max_mois
        ):
            raise ValueError("duree_min_mois > duree_max_mois")
        if self.secteur is not None:
            self.__dict__["secteur"] = self.secteur.lower().strip()
        if self.q is not None:
            self.__dict__["q"] = self.q.strip()
        return self


class GeolocationOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lat: float
    lng: float


class IntermediaireSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    nom: str
    geolocation: GeolocationOut | None = None
    url: str | None = None


class DocumentRequisOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    label: str
    format: str


class OffreListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offre_id: UUID
    nom: str
    intermediaire: IntermediaireSummary
    type: OffreType
    montant_min: Money | None = None
    montant_max: Money | None = None
    duree_min_mois: int | None = None
    duree_max_mois: int | None = None
    secteurs: list[str] = Field(default_factory=list)
    accepted_languages: list[str] = Field(default_factory=lambda: ["fr"])


class OffreListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OffreListItem]
    count: int
    next_cursor: str | None = None


class OffreDetailOut(OffreListItem):
    description: str = ""
    documents_requis: list[DocumentRequisOut] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    lien_externe: str | None = None
    source_id: UUID | None = None
