"""Helpers communs aux tools de visualisation F16.

Étend ``_common`` (F15) sans le modifier :
- ``AltTextMixin`` : impose ``alt_text`` non vide (accessibilité, aria-label).
- ``SourceRequiredMixin`` : impose ``source_ids`` non vide (sourçage F03).
- ``ensure_internal_link`` : valide qu'un lien commence par ``/`` (P7).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AltTextMixin(BaseModel):
    """Mixin imposant un ``alt_text`` non vide (accessibilité)."""

    model_config = ConfigDict(extra="forbid")

    alt_text: str = Field(min_length=1, max_length=512)


class SourceRequiredMixin(BaseModel):
    """Mixin imposant ``source_ids`` non vide (sourçage P1, F03)."""

    model_config = ConfigDict(extra="forbid")

    source_ids: list[int] = Field(min_length=1, max_length=20)


def ensure_internal_link(value: str) -> str:
    """Valide qu'un lien commence par ``/`` (chemin interne uniquement, P7).

    Lève ``ValueError`` sur lien vide ou non préfixé par ``/``.
    """
    if not value or not value.startswith("/") or value.startswith("//"):
        raise ValueError(
            "link must be an internal path starting with '/' (no external URL)"
        )
    return value


__all__ = ["AltTextMixin", "SourceRequiredMixin", "ensure_internal_link"]
