"""F09 US4 — Schémas Pydantic ``document_requis``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.catalog.criteres.dsl import DSLError, parse


class DocumentRequisBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_type: Literal["fonds", "intermediaire"]
    owner_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    type: Literal["juridique", "financier", "technique", "impact", "autre"] = "autre"
    required_when: dict[str, Any] | None = None
    source_id: uuid.UUID

    @field_validator("required_when")
    @classmethod
    def _validate_dsl(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        try:
            parse(v)
        except DSLError as exc:
            raise ValueError(f"DSL invalid: {exc}") from exc
        return v


class DocumentRequisCreate(DocumentRequisBase):
    pass


class DocumentRequisUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    type: Literal["juridique", "financier", "technique", "impact", "autre"] | None = None
    required_when: dict[str, Any] | None = None
    source_id: uuid.UUID | None = None

    @field_validator("required_when")
    @classmethod
    def _validate_dsl(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        try:
            parse(v)
        except DSLError as exc:
            raise ValueError(f"DSL invalid: {exc}") from exc
        return v


class DocumentRequisOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    name: str
    type: str
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
