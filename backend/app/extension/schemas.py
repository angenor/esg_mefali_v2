"""F33 - Pydantic schemas pour l'extension Chrome."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UrlPatternOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pattern: str
    pattern_type: Literal["wildcard", "regex"]
    nature: Literal["fonds", "intermediaire"]
    fonds_id: uuid.UUID | None = None
    intermediaire_id: uuid.UUID | None = None
    offre_id: uuid.UUID | None = None
    offre_label: str | None = None
    preferred_language: str | None = None


class UrlPatternListOut(BaseModel):
    items: list[UrlPatternOut]
    updated_at: datetime


class ProjetSummaryOut(BaseModel):
    id: uuid.UUID
    titre: str | None = None
    description_courte: str | None = None
    montant_amount: str | None = None
    montant_currency: str | None = None
    secteur: str | None = None
    pays: str | None = None


class ProfileSummaryOut(BaseModel):
    account_id: uuid.UUID
    raison_sociale: str | None = None
    secteur: str | None = None
    pays: str | None = None
    taille_effectifs: int | None = None
    projet: ProjetSummaryOut | None = None
    generated_at: datetime


class SuggestFieldIn(BaseModel):
    field_label: str = Field(..., min_length=1, max_length=300)
    field_max_length: int = Field(..., ge=1, le=10000)
    projet_id: uuid.UUID | None = None
    offre_id: uuid.UUID | None = None
    intermediaire_id: uuid.UUID | None = None
    language: Literal["fr", "en"] = "fr"


class SuggestFieldOut(BaseModel):
    text: str
    length: int
    source: Literal["llm", "fallback"]
    generated_at: datetime


class FieldMappingOut(BaseModel):
    intermediaire_id: uuid.UUID
    mapping_json: dict[str, Any]


class FieldMappingListOut(BaseModel):
    items: list[FieldMappingOut]


class AdminUrlPatternIn(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=500)
    pattern_type: Literal["wildcard", "regex"] = "wildcard"
    nature: Literal["fonds", "intermediaire"]
    fonds_id: uuid.UUID | None = None
    intermediaire_id: uuid.UUID | None = None
    offre_id: uuid.UUID | None = None
    is_active: bool = True
    preferred_language: str | None = Field(default=None, max_length=2)


class AdminUrlPatternUpdateIn(BaseModel):
    pattern: str | None = Field(default=None, min_length=1, max_length=500)
    pattern_type: Literal["wildcard", "regex"] | None = None
    nature: Literal["fonds", "intermediaire"] | None = None
    fonds_id: uuid.UUID | None = None
    intermediaire_id: uuid.UUID | None = None
    offre_id: uuid.UUID | None = None
    is_active: bool | None = None
    preferred_language: str | None = Field(default=None, max_length=2)


class AdminUrlPatternOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pattern: str
    pattern_type: str
    nature: str
    fonds_id: uuid.UUID | None = None
    intermediaire_id: uuid.UUID | None = None
    offre_id: uuid.UUID | None = None
    is_active: bool
    preferred_language: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminUrlPatternListOut(BaseModel):
    items: list[AdminUrlPatternOut]
    total: int
