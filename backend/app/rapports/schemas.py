"""F24 — Pydantic schemas pour les endpoints /me/rapports."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EntityType = Literal["entreprise", "projet"]
Language = Literal["fr", "en"]


class RapportCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: EntityType = "entreprise"
    entity_id: uuid.UUID
    referentiels: list[str] = Field(min_length=1, max_length=20)
    language: Language = "fr"

    @field_validator("referentiels")
    @classmethod
    def _strip_unique(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        seen: set[str] = set()
        out: list[str] = []
        for code in cleaned:
            if code not in seen:
                seen.add(code)
                out.append(code)
        if not out:
            raise ValueError("au moins un code de référentiel est requis")
        return out


class RapportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rapport_id: uuid.UUID
    entity_type: EntityType
    entity_id: uuid.UUID
    referentiels: list[str]
    language: Language
    file_size_bytes: int | None
    generated_at: datetime
    download_url: str


class RapportListOut(BaseModel):
    items: list[RapportOut]
    total: int
