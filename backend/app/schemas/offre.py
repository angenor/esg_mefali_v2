"""F08 — Pydantic schemas Offre (Fonds × Intermediaire)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.critere import Critere, Document

Lang = Literal["fr", "en"]


class OffreCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fonds_id: UUID
    intermediaire_id: UUID
    name: str = Field(min_length=1, max_length=200)
    accepted_languages: list[Lang] = ["fr"]
    deadline: datetime | None = None
    criteres_offre_specifiques: list[Critere] = []
    documents_specifiques: list[Document] = []
    frais_specifiques: dict[str, Any] = {}
    delais_specifiques: dict[str, Any] = {}
    source_ids: list[UUID] = []


class OffreUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    accepted_languages: list[Lang] | None = None
    deadline: datetime | None = None
    criteres_offre_specifiques: list[Critere] | None = None
    documents_specifiques: list[Document] | None = None
    frais_specifiques: dict[str, Any] | None = None
    delais_specifiques: dict[str, Any] | None = None
    source_ids: list[UUID] | None = None
