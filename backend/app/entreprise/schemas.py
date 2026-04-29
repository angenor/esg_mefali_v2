"""F11 — Pydantic v2 schemas pour le profil entreprise."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.entreprise.taxonomy import (
    ALLOWED_CURRENCIES,
    UEMOA_CEDEAO_ISO2,
    all_sector_codes,
)


class MoneyIn(BaseModel):
    """Type Money typé (amount + currency) — invariant Module 0 P5."""

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


def _check_iso2(v: str | None) -> str | None:
    if v is None:
        return None
    if len(v) != 2 or not v.isalpha():
        raise ValueError("must be ISO2 alpha-2")
    u = v.upper()
    if u not in UEMOA_CEDEAO_ISO2:
        raise ValueError(f"ISO2 must be one of UEMOA/CEDEAO: {sorted(UEMOA_CEDEAO_ISO2)}")
    return u


class EntreprisePatchIn(BaseModel):
    """Édition partielle. Tous les champs optionnels."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    secteur_code: str | None = None
    secteur_label: str | None = None
    taille_ca: MoneyIn | None = None
    taille_effectifs: int | None = Field(default=None, ge=0, le=10000)
    localisation_siege_pays_iso2: str | None = None
    localisation_siege_ville: str | None = Field(default=None, max_length=255)
    zones_operation_pays_iso2: list[str] | None = None
    gouvernance_json: dict[str, Any] | None = None
    pratiques_actuelles_json: dict[str, Any] | None = None

    @field_validator("secteur_code")
    @classmethod
    def _check_sector(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in all_sector_codes():
            raise ValueError("secteur_code unknown — use GET /me/entreprise/sectors")
        return v

    @field_validator("localisation_siege_pays_iso2")
    @classmethod
    def _check_pays(cls, v: str | None) -> str | None:
        return _check_iso2(v)

    @field_validator("zones_operation_pays_iso2")
    @classmethod
    def _check_zones(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        out: list[str] = []
        for x in v:
            checked = _check_iso2(x)
            if checked is None:
                raise ValueError("zones_operation_pays_iso2 entries must not be null")
            out.append(checked)
        return out


class EntreprisePutIn(EntreprisePatchIn):
    """PUT = même schéma (édition complète mais champs restent optionnels :
    la PME peut vider un champ explicitement)."""


class EntrepriseFieldMeta(BaseModel):
    """Métadonnées de provenance par champ."""

    model_config = ConfigDict(extra="forbid")

    source_of_change: str | None = None
    last_modified_at: datetime | None = None
    last_modified_by: UUID | None = None


class EntrepriseRead(BaseModel):
    """Lecture profil + métadonnées agrégées."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    account_id: UUID
    version: int

    name: str | None = None
    secteur_code: str | None = None
    secteur_label: str | None = None
    taille_ca: MoneyOut | None = None
    taille_effectifs: int | None = None
    localisation_siege_pays_iso2: str | None = None
    localisation_siege_ville: str | None = None
    zones_operation_pays_iso2: list[str] | None = None
    gouvernance_json: dict[str, Any] | None = None
    pratiques_actuelles_json: dict[str, Any] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    field_meta: dict[str, EntrepriseFieldMeta] = Field(default_factory=dict)


class CompletenessFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_code: str
    missing_fields: list[str]


class CompletenessOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    percentage: int
    missing_required_for_features: list[CompletenessFeature]


class ConflictOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = "version_conflict"
    message: str
    current_version: int
    your_version: int


class SectorOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    label: str
