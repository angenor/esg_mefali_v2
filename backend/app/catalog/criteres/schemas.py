"""F09 US3 — Schémas Pydantic ``critere``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.catalog.criteres.dsl import DSLError, parse


class CritereBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_type: Literal["fonds", "intermediaire", "offre", "referentiel"]
    owner_id: uuid.UUID
    label: str = Field(..., min_length=1, max_length=200)
    severity: Literal["blocking", "warning", "info"] = "warning"
    expression_json: dict[str, Any]
    source_id: uuid.UUID

    @field_validator("expression_json")
    @classmethod
    def _validate_dsl(cls, v: dict[str, Any]) -> dict[str, Any]:
        try:
            parse(v)
        except DSLError as exc:
            raise ValueError(f"DSL invalid: {exc}") from exc
        return v


class CritereCreate(CritereBase):
    pass


class CritereUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=200)
    severity: Literal["blocking", "warning", "info"] | None = None
    expression_json: dict[str, Any] | None = None
    source_id: uuid.UUID | None = None

    @field_validator("expression_json")
    @classmethod
    def _validate_dsl(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        try:
            parse(v)
        except DSLError as exc:
            raise ValueError(f"DSL invalid: {exc}") from exc
        return v


class CritereOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    label: str
    severity: str
    expression_json: dict[str, Any]
    source_id: uuid.UUID
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
