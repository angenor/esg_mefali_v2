"""F08 — Schemas Pydantic pour la réponse `/effective` (calcul fusionné)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.critere import Critere, Document


class EffectiveLayer(BaseModel):
    """Couche d'origine (Fonds ou Intermediaire) pour la traçabilité."""

    model_config = ConfigDict(extra="forbid")

    criteres: list[Critere] = []
    documents: list[Document] = []
    frais: dict[str, Any] = {}
    delais: dict[str, Any] = {}
    referentiel: dict[str, Any] | None = None
    deadline: datetime | None = None


class EffectiveResponse(BaseModel):
    """Réponse calculée pour GET /admin/offres/{id}/effective."""

    model_config = ConfigDict(extra="forbid")

    fonds_layer: EffectiveLayer
    intermediaire_layer: EffectiveLayer
    offre_layer: EffectiveLayer
    criteres_effectifs: list[Critere] = []
    documents_effectifs: list[Document] = []
    frais_effectifs: dict[str, Any] = {}
    delais_effectifs_jours: int = 0
    referentiel_effectif: dict[str, Any] | None = None
    accepted_languages: list[Literal["fr", "en"]] = ["fr"]
    deadline: datetime | None = None
    effective_warning: list[str] = []
    snapshot_hash: str = ""
