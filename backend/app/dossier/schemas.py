"""F26 - Pydantic schemas for dossier generation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DossierRequest(BaseModel):
    """Request body for POST /me/dossiers/generate."""

    model_config = ConfigDict(extra="forbid")

    projet_id: UUID
    offre_id: UUID
    langue: str = Field(default="fr", pattern="^fr$")


class DossierSource(BaseModel):
    """Citation/source attached to the generated dossier."""

    model_config = ConfigDict(extra="forbid")

    label: str
    url: str | None = None


class DossierResponse(BaseModel):
    """Response envelope for generated dossier."""

    model_config = ConfigDict(extra="forbid")

    sections: dict[str, str]
    sources: list[DossierSource]
    language: str
    metadata: dict[str, Any] = Field(default_factory=dict)
