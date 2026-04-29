"""F08 — Pydantic schemas Fonds source."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.critere import Critere, Document

FondsType = Literal["multilateral", "bilateral", "regional", "national", "prive"]
SubmissionMode = Literal["rolling", "call_for_proposals"]


class Money(BaseModel):
    """Money typed JSONB."""

    model_config = ConfigDict(extra="forbid")
    amount: float
    currency: Literal["XOF", "EUR", "USD", "GHS", "NGN", "MAD", "GBP"]


class FondsCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    organisation: str = Field(min_length=1, max_length=200)
    type: FondsType
    thematique: list[str] = []
    instruments: list[str] = []
    plafond_money: Money | None = None
    plancher_money: Money | None = None
    eligibilite_geo: list[str] = []
    submission_mode: SubmissionMode = "rolling"
    deadline: datetime | None = None
    referentiel_id: UUID | None = None
    criteres_json: list[Critere] = []
    documents_requis_json: list[Document] = []
    frais_json: dict[str, Any] = {}
    delais_json: dict[str, Any] = {}
    site_url: str | None = None
    contact_json: dict[str, Any] | None = None
    source_ids: list[UUID] = []

    @model_validator(mode="after")
    def _validate_deadline(self) -> FondsCreate:
        if self.submission_mode == "call_for_proposals" and self.deadline is None:
            raise ValueError("deadline required when submission_mode='call_for_proposals'")
        return self


class FondsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    organisation: str | None = None
    type: FondsType | None = None
    thematique: list[str] | None = None
    instruments: list[str] | None = None
    plafond_money: Money | None = None
    plancher_money: Money | None = None
    eligibilite_geo: list[str] | None = None
    submission_mode: SubmissionMode | None = None
    deadline: datetime | None = None
    criteres_json: list[Critere] | None = None
    documents_requis_json: list[Document] | None = None
    frais_json: dict[str, Any] | None = None
    delais_json: dict[str, Any] | None = None
    site_url: str | None = None
    contact_json: dict[str, Any] | None = None
    source_ids: list[UUID] | None = None
