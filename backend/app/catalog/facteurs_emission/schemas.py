"""F09 US5 — Schémas Pydantic ``facteur_emission``."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCOPES = ("1", "2", "3")
CATEGORIES = ("energie", "transport", "dechets", "achats", "autre")


class FacteurEmissionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=2, max_length=80)
    name: str = Field(..., min_length=1, max_length=200)
    valeur: Decimal = Field(..., ge=0)
    unite: str = Field(..., min_length=1, max_length=40)
    pays_iso2: str | None = Field(default=None, min_length=2, max_length=2)
    scope: Literal["1", "2", "3"]
    categorie: Literal["energie", "transport", "dechets", "achats", "autre"] = "autre"
    source_id: uuid.UUID
    valid_from_date: date

    @field_validator("pays_iso2")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class FacteurEmissionCreate(FacteurEmissionBase):
    pass


class FacteurEmissionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    valeur: Decimal | None = Field(default=None, ge=0)
    unite: str | None = Field(default=None, min_length=1, max_length=40)
    pays_iso2: str | None = Field(default=None, min_length=2, max_length=2)
    scope: Literal["1", "2", "3"] | None = None
    categorie: Literal["energie", "transport", "dechets", "achats", "autre"] | None = None
    source_id: uuid.UUID | None = None
    valid_from_date: date | None = None
    valid_to_date: date | None = None


class FacteurEmissionOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: uuid.UUID
    code: str
    name: str
    valeur: Decimal
    unite: str
    pays_iso2: str | None
    scope: str
    categorie: str
    source_id: uuid.UUID
    version: int
    valid_from_date: date
    valid_to_date: date | None
    status: str
    created_at: datetime
    updated_at: datetime
