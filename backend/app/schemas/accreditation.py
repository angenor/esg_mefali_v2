"""F08 — Pydantic schemas Accréditation (relation datée Fonds×Intermediaire)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.fonds_source import Money


class AccreditationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intermediaire_id: UUID
    fonds_id: UUID
    valid_from: date
    valid_to: date | None = None
    plafond_money: Money | None = None
    source_id: UUID
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_dates(self) -> AccreditationCreate:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be >= valid_from")
        return self


class AccreditationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_from: date | None = None
    valid_to: date | None = None
    plafond_money: Money | None = None
    source_id: UUID | None = None
    notes: str | None = None
