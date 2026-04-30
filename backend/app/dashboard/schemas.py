"""F32 — Schemas Pydantic pour le dashboard PME (lecture seule).

Schemas exposés :
- ``DashboardSummaryOut`` : agrégat optimisé pour la page d'accueil.
- ``DataExportOut`` : export JSON complet du compte (US6 "Mes données").
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class ScoreEntry(BaseModel):
    """Dernier score persisté pour un référentiel donné (entité = entreprise)."""

    model_config = ConfigDict(from_attributes=True)

    referentiel_code: str
    referentiel_version: int
    score_global: Decimal | None
    coverage_ratio: Decimal | None
    computed_at: datetime


class CarbonEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year: int
    total_tco2e: Decimal
    computed_at: datetime


class CreditScoreEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    solvabilite: int
    impact_vert: int
    combine: int
    methodologie_version: int
    coherence_warning: bool
    computed_at: datetime


class CandidatureItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    projet_id: uuid.UUID
    offre_id: uuid.UUID
    statut: str | None
    soumission_at: datetime | None
    created_at: datetime | None


class CandidatureBlock(BaseModel):
    counters_by_statut: dict[str, int]
    total: int
    recent: list[CandidatureItem]


class RapportItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    referentiels: list[str]
    language: str
    generated_at: datetime


class RapportBlock(BaseModel):
    total: int
    recent: list[RapportItem]


class AttestationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_id: uuid.UUID
    generated_at: datetime
    valid_until: datetime
    revoked_at: datetime | None


class AttestationBlock(BaseModel):
    active: int
    revoked: int
    recent: list[AttestationItem]


class ActionStepEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    category: str
    priority: str
    status: str
    horizon_at: date


class DashboardSummaryOut(BaseModel):
    account_id: uuid.UUID
    scores: list[ScoreEntry]
    carbon: list[CarbonEntry]
    credit_score: CreditScoreEntry | None
    candidatures: CandidatureBlock
    rapports: RapportBlock
    attestations: AttestationBlock
    next_actions: list[ActionStepEntry]
    generated_at: datetime


class DataExportOut(BaseModel):
    account: dict[str, Any]
    entreprise: dict[str, Any] | None
    projets: list[dict[str, Any]]
    candidatures: list[dict[str, Any]]
    scores: list[dict[str, Any]]
    carbon: list[dict[str, Any]]
    credit_score: dict[str, Any] | None
    rapports: list[dict[str, Any]]
    attestations: list[dict[str, Any]]
    consents: list[dict[str, Any]]
    action_plan: list[dict[str, Any]]
    exported_at: datetime
