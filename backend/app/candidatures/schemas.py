"""F34 — Schémas Pydantic pour ``/me/candidatures``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
    progression_pct: int = 0
    created_at: datetime
    updated_at: datetime


class CandidatureStatusUpdateIn(BaseModel):
    """Body de ``PATCH /me/candidatures/{id}/status``."""

    statut: CandidatureStatut


class CandidatureStatusOut(BaseModel):
    """Réponse de ``PATCH /me/candidatures/{id}/status``."""

    id: uuid.UUID
    statut: str
    version: int
    updated_at: datetime
