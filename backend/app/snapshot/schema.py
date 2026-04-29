"""F04 — Pydantic v2 mirror of contracts/snapshot.schema.json (CandidatureSnapshotV1)."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_AMOUNT_RE = re.compile(r"^-?\d+(\.\d+)?$")


class Money(BaseModel):
    """Strict Money tuple (amount string + ISO 4217 currency)."""

    model_config = ConfigDict(extra="forbid")

    amount: str
    currency: str

    @field_validator("amount")
    @classmethod
    def _check_amount(cls, v: str) -> str:
        if not _AMOUNT_RE.match(v):
            raise ValueError("amount must match pattern ^-?\\d+(\\.\\d+)?$")
        return v

    @field_validator("currency")
    @classmethod
    def _check_currency(cls, v: str) -> str:
        if not _CURRENCY_RE.match(v):
            raise ValueError("currency must be a 3-letter ISO 4217 code")
        return v

    def to_decimal(self) -> Decimal:
        return Decimal(self.amount)


class ReferentielRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    logical_id: UUID
    version: Annotated[int, Field(ge=1)]
    valid_from: datetime


class CritereRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    logical_id: UUID
    version: Annotated[int, Field(ge=1)]


class OffreRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    criteres: list[CritereRef] = Field(default_factory=list)


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID
    verified: bool


class SnapshotScores(BaseModel):
    model_config = ConfigDict(extra="forbid")
    global_: Money = Field(alias="global")
    per_critere: dict[str, Money] = Field(default_factory=dict)


class CandidatureSnapshotV1(BaseModel):
    """Frozen representation of a Candidature at submission time.

    All version-bearing references are pinned (logical_id + version) so the
    submission can be recomputed deterministically even after the catalogue
    has evolved.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: str = Field(default="1")
    referentiel: ReferentielRef
    offre: OffreRef
    projet_state: dict[str, Any] = Field(default_factory=dict)
    scores: SnapshotScores
    sources: list[SourceRef] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, v: str) -> str:
        if v != "1":
            raise ValueError("schema_version must be '1' for v1 snapshots")
        return v
