"""Pydantic v2 schémas (strict ``extra='forbid'``) — F03 Source."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceVerificationStatus(StrEnum):
    pending = "pending"
    verified = "verified"
    outdated = "outdated"
    rejected = "rejected"


class SourceRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    url: HttpUrl
    title: str
    publisher: str
    version: str | None = None
    date_publi: date | None = None
    page: str | None = None
    section: str | None = None
    captured_at: datetime
    verified_at: datetime | None = None
    verification_status: SourceVerificationStatus
    notes: str | None = None


class SourceList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SourceRead]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class UnsourcedClaimAggRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    freq: int = Field(ge=1)
    last_seen: datetime


class ToolErrorCode(StrEnum):
    not_verified = "not_verified"
    not_found = "not_found"


class ToolError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: ToolErrorCode
    message: str


# --- LLM Tool I/O schémas (P9) ---

class CiteSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID


class CiteSourceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: SourceRead | None = None
    error: Literal["not_verified", "not_found"] | None = None


class SearchSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=256)
    publisher: str | None = Field(default=None, max_length=100)
    k: int = Field(default=10, ge=1, le=50)


class SearchSourceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[SourceRead]


class FlagUnsourcedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str = Field(min_length=1, max_length=2000)
    context: dict = Field(default_factory=dict)


class FlagUnsourcedOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
