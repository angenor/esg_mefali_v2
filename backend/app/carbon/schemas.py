"""F28 - Schemas Pydantic pour endpoints carbone."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CarbonSourceItem(BaseModel):
    """Une entree du source_data (un poste a calculer)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., ge=0)
    country: str | None = Field(default=None, min_length=2, max_length=2)


class CarbonComputeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int = Field(..., ge=2000, le=2100)
    source_data: list[CarbonSourceItem] = Field(..., min_length=1)


class CarbonBreakdownLineOut(BaseModel):
    code: str
    quantity: Decimal
    unit: str
    factor_id: UUID
    factor_value: Decimal
    factor_source_id: UUID
    factor_version: int
    scope: str
    categorie: str
    kgco2e: Decimal


class CarbonResultOut(BaseModel):
    id: UUID
    year: int
    total_tco2e: Decimal
    by_scope_kgco2e: dict[str, Decimal]
    by_category_kgco2e: dict[str, Decimal]
    breakdown: list[CarbonBreakdownLineOut]
    factor_versions: list[dict[str, Any]]


class ReductionPlanOut(BaseModel):
    year: int
    actions: list[dict[str, Any]]
