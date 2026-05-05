"""F28 + F47 - Schemas Pydantic pour endpoints carbone."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CarbonSourceItem(BaseModel):
    """Une entree du source_data (un poste a calculer).

    F47 : ajout du champ optionnel ``source_id`` (UUID de la Source vérifiée).
    None est accepté pour rétrocompat avec les imports F28 pré-F47 et avec
    POST /me/carbon/compute. POST /me/carbon/{year}/edit-line exige source_id
    non null (vérifié au niveau service via _assert_source_verified).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., ge=0)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    source_id: UUID | None = Field(default=None)


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


# ====================================================================
# F47 — nouveaux DTO
# ====================================================================


class CarbonIndexEntryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    footprint_id: UUID
    year: int
    total_tco2e: Decimal
    computed_at: datetime
    version: int


class CarbonIndexOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[CarbonIndexEntryOut]


class CarbonRecomputeResponse(CarbonResultOut):
    """Identique à CarbonResultOut + previous_footprint_id (None si premier calcul)."""

    previous_footprint_id: UUID | None = None


class CarbonEditLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., ge=0)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    source_id: UUID  # OBLIGATOIRE


class CarbonEditLineResponse(CarbonResultOut):
    previous_footprint_id: UUID
    edited_line_code: str
