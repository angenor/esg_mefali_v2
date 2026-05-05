"""F52 US3 — Schémas Pydantic des exports historiques.

- ``ExportCreate`` : création d'un export avec validation des combinaisons
  ``(type, format)`` autorisées et cohérence des IDs croisés.
- ``ExportOut`` : représentation d'un export (signed_url masquée si expirée).
- ``ExportListOut`` : pagination keyset.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ExportTypeLiteral = Literal[
    "rgpd_full", "report_pdf", "attestation_pdf", "dossier_pdf"
]
ExportStatusLiteral = Literal["pending", "ready", "expired", "failed"]
ExportFormatLiteral = Literal["pdf", "json"]
ExportDeliveredViaLiteral = Literal["inapp", "email"]

# Combinaisons autorisées : (type → required_id_field, allowed_format)
_TYPE_RULES: dict[str, tuple[str | None, str]] = {
    "rgpd_full": (None, "json"),
    "report_pdf": ("report_id", "pdf"),
    "attestation_pdf": ("attestation_id", "pdf"),
    "dossier_pdf": ("candidature_id", "pdf"),
}


class ExportCreate(BaseModel):
    """Body de ``POST /me/exports``."""

    model_config = ConfigDict(extra="forbid")

    type: ExportTypeLiteral
    format: ExportFormatLiteral
    report_id: uuid.UUID | None = None
    attestation_id: uuid.UUID | None = None
    candidature_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _consistency(self) -> ExportCreate:
        rule = _TYPE_RULES.get(self.type)
        if rule is None:  # pragma: no cover — Literal couvre les valeurs valides
            raise ValueError(f"Type d'export inconnu : {self.type}")
        required_field, allowed_format = rule
        if self.format != allowed_format:
            raise ValueError(
                f"format={self.format!r} incompatible avec type={self.type!r} "
                f"(attendu {allowed_format!r})"
            )
        # Vérification présence de l'ID requis et absence des autres
        all_id_fields = ("report_id", "attestation_id", "candidature_id")
        for field_name in all_id_fields:
            value = getattr(self, field_name)
            if field_name == required_field:
                if value is None:
                    raise ValueError(
                        f"type={self.type!r} requiert le champ {field_name!r}"
                    )
            elif value is not None:
                raise ValueError(
                    f"type={self.type!r} interdit le champ {field_name!r}"
                )
        return self


class ExportOut(BaseModel):
    """Représentation d'un export pour ``GET /me/exports``."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ExportTypeLiteral
    format: ExportFormatLiteral
    size_bytes: int | None = None
    status: ExportStatusLiteral
    created_at: datetime
    ready_at: datetime | None = None
    signed_url: str | None = None
    signed_url_expires_at: datetime | None = None
    delivered_via: ExportDeliveredViaLiteral | None = None


class ExportListOut(BaseModel):
    """Réponse paginée de ``GET /me/exports``."""

    model_config = ConfigDict(extra="forbid")

    items: list[ExportOut] = Field(default_factory=list)
    next_cursor: str | None = None
