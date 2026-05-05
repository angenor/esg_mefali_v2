"""F29 + F48 - Schemas Pydantic pour le credit scoring."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreditDataKind(StrEnum):
    MOBILE_MONEY = "mobile_money"
    DECLARATIF = "declaratif"
    PHOTOS = "photos"
    PUBLIQUE = "publique"


class CreditDataIn(BaseModel):
    """Payload du POST /me/credit-data (declaratif/photos/publique)."""

    model_config = ConfigDict(extra="forbid")
    kind: CreditDataKind
    payload: dict[str, Any] = Field(default_factory=dict)
    valid_until: datetime | None = None


class CreditDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: CreditDataKind
    payload_json: dict[str, Any]
    uploaded_at: datetime
    valid_until: datetime | None = None


class FactorOut(BaseModel):
    name: str
    definition: str
    value: float | None
    weight: float
    contribution: float
    source_id: str
    axis: str


class CreditScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entreprise_id: uuid.UUID
    solvabilite: int = Field(ge=0, le=100)
    impact_vert: int = Field(ge=0, le=100)
    combine: int = Field(ge=0, le=100)
    facteurs: list[dict[str, Any]]
    methodologie_version: int
    coherence_warning: bool
    computed_at: datetime
    # F48 — additif, optionnel (rétrocompat).
    subscores: dict[str, int | None] | None = None


class MethodologyOut(BaseModel):
    version: int
    alpha: float
    beta: float
    factors: list[dict[str, Any]]
    referentiel_id: uuid.UUID | None = None
    status: str = "published"
    description: str | None = None


# --------------------------------------------------------------------------- #
# F48 — Historique (US7)                                                      #
# --------------------------------------------------------------------------- #


class ScoreHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: uuid.UUID
    combine: int = Field(ge=0, le=100)
    solvabilite: int = Field(ge=0, le=100)
    impact_vert: int = Field(ge=0, le=100)
    subscores: dict[str, int | None] | None = None
    methodologie_version: int
    computed_at: datetime
    coherence_warning: bool


class ScoreHistoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ScoreHistoryEntry]


# --------------------------------------------------------------------------- #
# F48 — Eligibility (US3)                                                     #
# --------------------------------------------------------------------------- #


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    INCOMPLETE = "incomplete"


class CriterionEvalOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    label: str
    threshold: str | None
    actual: str | None
    met: bool
    blocking: bool


class EligibilityBadgeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    label: str
    description: str
    status: EligibilityStatus
    primary_reason: str | None
    criteria: list[CriterionEvalOut]
    matching_offer_query: str
    source_id: uuid.UUID
    version: int
    valid_from: datetime
    valid_to: datetime | None


class EligibilityListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[EligibilityBadgeOut]
    evaluated_at: datetime
    catalog_version_max: int


# --------------------------------------------------------------------------- #
# F48 — Recommendations (US4)                                                 #
# --------------------------------------------------------------------------- #


class CreditRecommendationOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: uuid.UUID
    title: str
    description: str | None
    target_subscore: str
    estimated_credit_points_impact: int = Field(gt=0)


class CreditRecommendationsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CreditRecommendationOut]
    selected_subscores: list[str]
