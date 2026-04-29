"""F08 — Pydantic schemas Intermédiaire."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.critere import Critere, Document

IntermediaireType = Literal[
    "DAE", "NIE", "RIE", "MIE",
    "banque_locale", "dev_carbone", "agence_nationale", "agence_implem",
]


class IntermediaireCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    type: IntermediaireType
    pays: list[str] = []
    zone_op: str | None = None
    contact_json: dict[str, Any] | None = None
    frais_json: dict[str, Any] = {}
    delais_json: dict[str, Any] = {}
    criteres_json: list[Critere] = []
    documents_requis_json: list[Document] = []
    referentiel_id: UUID | None = None
    portail_url: str | None = None
    track_record_json: dict[str, Any] | None = None
    source_ids: list[UUID] = []


class IntermediaireUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    type: IntermediaireType | None = None
    pays: list[str] | None = None
    zone_op: str | None = None
    contact_json: dict[str, Any] | None = None
    frais_json: dict[str, Any] | None = None
    delais_json: dict[str, Any] | None = None
    criteres_json: list[Critere] | None = None
    documents_requis_json: list[Document] | None = None
    portail_url: str | None = None
    track_record_json: dict[str, Any] | None = None
    source_ids: list[UUID] | None = None
