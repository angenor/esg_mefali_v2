"""F09 US2 — Schémas Pydantic ``referentiel``."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReferentielBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=2, max_length=80)
    name: str = Field(..., min_length=1, max_length=200)
    publisher: str = Field(default="", max_length=200)
    type: Literal["fonds", "intermediaire", "transverse", "interne"] = "transverse"
    formula_type: Literal["weighted_sum", "custom"] = "weighted_sum"
    formula_expression: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _check_custom_formula(self) -> ReferentielBase:
        if self.formula_type == "custom" and not (self.formula_expression and self.formula_expression.strip()):
            raise ValueError("formula_expression required when formula_type='custom'")
        return self


class ReferentielCreate(ReferentielBase):
    source_ids: list[uuid.UUID] = Field(default_factory=list)


class ReferentielUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    publisher: str | None = Field(default=None, max_length=200)
    type: Literal["fonds", "intermediaire", "transverse", "interne"] | None = None
    formula_type: Literal["weighted_sum", "custom"] | None = None
    formula_expression: str | None = Field(default=None, max_length=4000)
    source_ids: list[uuid.UUID] | None = None


class ReferentielOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: uuid.UUID
    code: str
    name: str
    publisher: str
    type: str
    formula_type: str
    formula_expression: str | None = None
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
    source_ids: list[uuid.UUID] = Field(default_factory=list)


class IndicateurAttach(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicateur_id: uuid.UUID
    poids: Decimal = Field(..., ge=0)
    seuil_min: Decimal | None = None
    seuil_max: Decimal | None = None
    source_id: uuid.UUID
