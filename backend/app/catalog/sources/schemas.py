"""F07 — Pydantic schémas (subset MVP P1) pour le catalogue Sources.

Tous les modèles utilisent ``model_config = ConfigDict(extra='forbid')`` pour
rejeter strictement les champs inconnus (sécurité by-default).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    title: str = Field(min_length=1, max_length=500)
    publisher: str = Field(min_length=1, max_length=200)
    version: str | None = Field(default=None, max_length=50)
    date_publi: date | None = None
    page: str | None = Field(default=None, max_length=50)
    section: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class SourceUpdate(BaseModel):
    """PATCH partiel — tous les champs optionnels."""

    model_config = ConfigDict(extra="forbid")

    url: HttpUrl | None = None
    title: str | None = Field(default=None, min_length=1, max_length=500)
    publisher: str | None = Field(default=None, min_length=1, max_length=200)
    version: str | None = Field(default=None, max_length=50)
    date_publi: date | None = None
    page: str | None = Field(default=None, max_length=50)
    section: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class SourceRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    url: HttpUrl
    canonical_url: str
    title: str
    publisher: str
    version: str | None = None
    date_publi: date | None = None
    page: str | None = None
    section: str | None = None
    captured_at: datetime
    captured_by: UUID
    verified_by: UUID | None = None
    verified_at: datetime | None = None
    verification_status: Literal["pending", "verified", "outdated", "rejected"]
    notes: str | None = None


class SourceCreated(BaseModel):
    """Réponse 201 sur ``POST /admin/sources``."""

    model_config = ConfigDict(extra="forbid")

    source: SourceRead
    head_warning: str | None = None


class DuplicateConflict(BaseModel):
    """Réponse 409 sur doublon canonical_url + page."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["duplicate_source"] = "duplicate_source"
    message: str
    existing_id: UUID
