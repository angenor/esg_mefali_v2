"""F29 - Schemas Pydantic pour le credit scoring."""

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


class MethodologyOut(BaseModel):
    version: int
    alpha: float
    beta: float
    factors: list[dict[str, Any]]
    referentiel_id: uuid.UUID | None = None
    status: str = "published"
    description: str | None = None
