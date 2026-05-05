"""F34/F51 — Schémas Pydantic pour ``/me/candidatures``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CandidatureStatut = Literal[
    "brouillon",
    "soumise",
    "en_instruction",
    "acceptee",
    "refusee",
]

VALID_CANDIDATURE_STATUTS: frozenset[str] = frozenset(
    {"brouillon", "soumise", "en_instruction", "acceptee", "refusee"}
)


class CandidatureRowOut(BaseModel):
    """Ligne renvoyée par ``GET /me/candidatures``."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    projet_id: uuid.UUID
    offre_id: uuid.UUID
    statut: str | None = None
    step_courant: int = 1
    progression_pct: int = 0
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None


class CandidatureStatusUpdateIn(BaseModel):
    """Body de ``PATCH /me/candidatures/{id}/status``."""

    statut: CandidatureStatut


class CandidatureStatusOut(BaseModel):
    """Réponse de ``PATCH /me/candidatures/{id}/status``."""

    id: uuid.UUID
    statut: str
    version: int
    updated_at: datetime


# ---------- F51 — Wizard ----------


class WizardDraftIn(BaseModel):
    """Body de ``PATCH /me/candidatures/{id}/draft``."""

    model_config = ConfigDict(extra="forbid")

    step_courant: int | None = Field(default=None, ge=1, le=5)
    draft_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    expected_version: int = Field(ge=1)


class WizardDraftOut(BaseModel):
    """Réponse de ``PATCH /me/candidatures/{id}/draft``."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    step_courant: int
    progression_pct: int
    draft_snapshot_json: dict[str, Any]
    version: int
    updated_at: datetime


class WizardSubmitIn(BaseModel):
    """Body de ``POST /me/candidatures/{id}/submit``."""

    model_config = ConfigDict(extra="forbid")

    confirmed: bool
    expected_version: int = Field(ge=1)
    user_acknowledged_intangible: bool


class WizardSubmitOut(BaseModel):
    """Réponse de ``POST /me/candidatures/{id}/submit``."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    statut: str
    submitted_at: datetime
    snapshot_schema_version: str
    version: int


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime
    event: str
    by: str | None = None
    field: str | None = None
    from_value: Any | None = Field(default=None, alias="from")
    to_value: Any | None = Field(default=None, alias="to")
    comment: str | None = None


class CandidatureOffreSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    nom: str | None = None
    intermediaire_nom: str | None = None
    type: str | None = None
    montant_min: dict[str, Any] | None = None
    montant_max: dict[str, Any] | None = None
    documents_requis: list[dict[str, Any]] = Field(default_factory=list)


class CandidatureProjetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    titre: str | None = None
    description: str | None = None


class CandidatureDocumentLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID
    checklist_key: str | None = None
    filename: str | None = None
    uploaded_at: datetime | None = None


class CandidatureDetailOut(BaseModel):
    """Réponse de ``GET /me/candidatures/{id}``."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    offre: CandidatureOffreSummary
    projet: CandidatureProjetSummary
    statut: str
    step_courant: int
    progression_pct: int
    draft_snapshot_json: dict[str, Any]
    submitted_at: datetime | None = None
    submitted_snapshot_json: dict[str, Any] | None = None
    timeline: list[TimelineEvent] = Field(default_factory=list)
    documents_lies: list[CandidatureDocumentLink] = Field(default_factory=list)
    version: int
