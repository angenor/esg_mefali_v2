"""F25 — Schémas DTO pour le matching projet <-> offre.

DTO immutables (`frozen=True`). Money typé via `app.schemas.money`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.schemas.money import Money


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
