"""F09 US1 — Schémas Pydantic v2 ``indicateur``."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PILLARS = ("E", "S", "G", "transverse")
VALUE_TYPES = ("numeric", "percentage", "boolean", "enum", "text")
CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class IndicateurBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(..., min_length=2, max_length=80)
    name: str = Field(..., min_length=1, max_length=200)
    definition: str = Field(default="", max_length=4000)
    pillar: Literal["E", "S", "G", "transverse"]
    unite: str = Field(..., min_length=1, max_length=40)
    value_type: Literal["numeric", "percentage", "boolean", "enum", "text"]
    enum_values: list[str] | None = None

    @field_validator("code")
    @classmethod
    def _code_format(cls, v: str) -> str:
        v = v.strip().upper()
        if not CODE_RE.match(v):
            raise ValueError("code must match ^[A-Z][A-Z0-9_]*$ (UPPER_SNAKE_CASE)")
        return v

    @model_validator(mode="after")
    def _enum_values_required(self) -> IndicateurBase:
        if self.value_type == "enum":
            if not self.enum_values or len(self.enum_values) == 0:
                raise ValueError("enum_values required when value_type='enum'")
        else:
            if self.enum_values is not None:
                raise ValueError("enum_values must be null unless value_type='enum'")
        return self


class IndicateurCreate(IndicateurBase):
    """Payload for ``POST /admin/indicateurs``. Sources fournies séparément."""

    source_ids: list[uuid.UUID] = Field(default_factory=list)


class IndicateurUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    definition: str | None = Field(default=None, max_length=4000)
    pillar: Literal["E", "S", "G", "transverse"] | None = None
    unite: str | None = Field(default=None, min_length=1, max_length=40)
    value_type: Literal["numeric", "percentage", "boolean", "enum", "text"] | None = None
    enum_values: list[str] | None = None
    source_ids: list[uuid.UUID] | None = None


class IndicateurOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: uuid.UUID
    code: str
    name: str
    definition: str
    pillar: str
    unite: str
    value_type: str
    enum_values: list[str] | None = None
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
    source_ids: list[uuid.UUID] = Field(default_factory=list)


def serialize_out(row: dict[str, Any], source_ids: list[uuid.UUID]) -> dict[str, Any]:
    """Strip raw row to JSON-friendly dict suitable for ``IndicateurOut``."""
    out = {k: v for k, v in row.items() if not k.startswith("_")}
    out["source_ids"] = [str(s) for s in source_ids]
    return out
