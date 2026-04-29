"""F08 — Pydantic schemas pour les structures JSONB partagées (Critere, Document)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Critere(BaseModel):
    """Critère typé stocké en JSONB sur Fonds, Intermediaire, Offre."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=100)
    operator: Literal["eq", "min", "max", "in", "not_in", "contains"]
    value: Any
    unit: str | None = None
    source_id: UUID


class Document(BaseModel):
    """Document requis attaché à un Fonds, Intermediaire ou Offre."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    label: str
    type: Literal["identite", "financier", "technique", "esg", "juridique", "autre"]
    required: bool = True
    source_id: UUID | None = None
