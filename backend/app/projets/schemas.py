"""F12 - Pydantic v2 schemas pour les projets et documents projet."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.projets.validators import (
    ALLOWED_MATURITES,
    ALLOWED_STATUTS,
    ALLOWED_STRUCTURES_FINANCEMENT,
    ALLOWED_TYPES_IMPACT,
)

# Same allowed currencies as F11.
ALLOWED_CURRENCIES = frozenset({"XOF", "EUR", "USD"})


class MoneyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def _check_currency(cls, v: str) -> str:
        u = v.upper()
        if u not in ALLOWED_CURRENCIES:
            raise ValueError(f"currency must be one of {sorted(ALLOWED_CURRENCIES)}")
        return u


class MoneyOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal
    currency: str


class IndicateurImpactItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=128)
    value: float
    unit: str = Field(min_length=1, max_length=32)


class ProjetBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    objectif_environnemental: str | None = None
    types_impact: list[str] | None = None
    maturite: str | None = None
    montant_recherche: MoneyIn | None = None
    duree_mois: int | None = Field(default=None, ge=0, le=600)
    structure_financement_arr: list[str] | None = None
    indicateurs_impact_json: list[IndicateurImpactItem] | None = None
    localisation_pays_iso2: str | None = None
    localisation_ville: str | None = Field(default=None, max_length=255)
    statut: str | None = None

    @field_validator("types_impact")
    @classmethod
    def _check_types_impact(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        for x in v:
            if x not in ALLOWED_TYPES_IMPACT:
                raise ValueError(f"types_impact: {x} non autorise")
        return v

    @field_validator("structure_financement_arr")
    @classmethod
    def _check_structure(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        for x in v:
            if x not in ALLOWED_STRUCTURES_FINANCEMENT:
                raise ValueError(f"structure_financement: {x} non autorise")
        return v

    @field_validator("statut")
    @classmethod
    def _check_statut(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_STATUTS:
            raise ValueError(f"statut invalide: {v}")
        return v

    @field_validator("maturite")
    @classmethod
    def _check_maturite(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_MATURITES:
            raise ValueError(f"maturite invalide: {v}")
        return v

    @field_validator("localisation_pays_iso2")
    @classmethod
    def _check_pays(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) != 2 or not v.isalpha():
            raise ValueError("localisation_pays_iso2 must be ISO2 alpha-2")
        return v.upper()


class ProjetCreate(ProjetBase):
    """Creation d'un projet : nom obligatoire, statut par defaut brouillon."""

    nom: str = Field(min_length=1, max_length=255)


class ProjetPatch(ProjetBase):
    """PATCH - tous champs optionnels."""


class ProjetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    nom: str
    statut: str | None = None
    types_impact: list[str] | None = None
    maturite: str | None = None
    montant_recherche: MoneyOut | None = None
    updated_at: datetime | None = None


class ProjetRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    account_id: UUID
    entreprise_id: UUID | None = None
    version: int

    nom: str
    description: str | None = None
    objectif_environnemental: str | None = None
    types_impact: list[str] | None = None
    maturite: str | None = None
    montant_recherche: MoneyOut | None = None
    duree_mois: int | None = None
    structure_financement_arr: list[str] | None = None
    indicateurs_impact_json: list[dict[str, Any]] | None = None
    localisation_pays_iso2: str | None = None
    localisation_ville: str | None = None
    statut: str | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class TransitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to: str

    @field_validator("to")
    @classmethod
    def _check_to(cls, v: str) -> str:
        if v not in ALLOWED_STATUTS:
            raise ValueError(f"statut invalide: {v}")
        return v


class ConflictOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = "version_conflict"
    message: str
    current_version: int
    your_version: int


class DocumentProjetRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    projet_id: UUID
    name: str
    original_filename: str
    mime_type: str
    size_bytes: int
    type: str
    uploaded_by: UUID | None = None
    created_at: datetime | None = None


class ProjetListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ProjetSummary]
    total: int
    page: int
    limit: int
