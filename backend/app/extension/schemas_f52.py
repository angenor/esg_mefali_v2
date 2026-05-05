"""F52 US4 — Schémas Pydantic pour le sidepanel & le ping de l'extension.

Sépare les ajouts F52 du fichier ``schemas.py`` historique (F33).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ExtensionPingIn(BaseModel):
    """Heartbeat envoyé par le service worker (UPSERT côté backend)."""

    model_config = ConfigDict(extra="forbid")

    extension_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    user_agent_summary: str = Field(max_length=255)


class ExtensionStatusOut(BaseModel):
    """Réponse de ``GET /me/extension/status`` (US5)."""

    model_config = ConfigDict(extra="forbid")

    detected: bool
    extension_version: str | None = None
    last_ping_at: datetime | None = None


class SidepanelCandidatureItem(BaseModel):
    """Une candidature active à afficher dans le panneau."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    offer_label: str
    deadline_at: datetime
    completion_pct: int = Field(ge=0, le=100)
    resume_url: HttpUrl


class SidepanelOfferItem(BaseModel):
    """Une offre recommandée affichée dans le panneau."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    label: str
    match_score: float = Field(ge=0.0, le=1.0)
    matching_url: HttpUrl


class SidepanelContextOut(BaseModel):
    """Contexte projeté côté sidepanel pour un host/path donné."""

    model_config = ConfigDict(extra="forbid")

    matched_offer_ids: list[uuid.UUID] = Field(default_factory=list)
    active_candidatures: list[SidepanelCandidatureItem] = Field(default_factory=list)
    recommended_offers: list[SidepanelOfferItem] = Field(default_factory=list)
