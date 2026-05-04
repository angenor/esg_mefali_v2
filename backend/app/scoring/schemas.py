"""F23 — Pydantic schemas pour les endpoints /me/scoring."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CoveredIndicatorOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicateur_id: uuid.UUID
    indicateur_code: str
    pillar: str
    value: Any | None = None
    normalized_value: float | None = None
    weight: float
    contribution: float
    source_id: uuid.UUID


class MissingIndicatorOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicateur_id: uuid.UUID
    indicateur_code: str
    pillar: str
    reason: str


class ScoreSummaryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    referentiel_code: str
    referentiel_id: uuid.UUID
    referentiel_version: int
    score_global: float | None = None
    scores_by_pillar: dict[str, float | None] = Field(default_factory=dict)
    coverage_ratio: float | None = None
    computed_at: datetime


class ScoreDetailOut(ScoreSummaryOut):
    indicateurs_couverts: list[CoveredIndicatorOut] = Field(default_factory=list)
    indicateurs_manquants: list[MissingIndicatorOut] = Field(default_factory=list)
    sources_used: list[uuid.UUID] = Field(default_factory=list)


class ScoreListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str
    entity_id: uuid.UUID
    scores: list[ScoreSummaryOut] = Field(default_factory=list)


# ---- F46 — endpoint history --------------------------------------------------


class ScoreHistoryEntry(BaseModel):
    """Une entrée d'historique de calcul (lecture pure ; pas d'audit)."""

    model_config = ConfigDict(extra="forbid")

    score_calculation_id: uuid.UUID
    computed_at: datetime
    score_global: float | None = None
    referentiel_version: int


class ScoreHistoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str
    entity_id: uuid.UUID
    referentiel_code: str
    entries: list[ScoreHistoryEntry] = Field(default_factory=list)
