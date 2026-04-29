"""Helpers communs aux tools de réponse F15.

- ``Option`` : modèle des choix proposés (value/label/description).
- ``no_html`` : validator partagé interdisant ``<`` / ``>`` dans les
  champs textuels exposés à l'utilisateur (anti-XSS minimal côté
  serveur ; sanitize approfondie côté frontend).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

_HTML_TAG_RE = re.compile(r"[<>]")


def no_html(value: str) -> str:
    """Refuse toute valeur contenant ``<`` ou ``>`` (anti-XSS)."""
    if _HTML_TAG_RE.search(value):
        raise ValueError("HTML tags forbidden in user-facing label")
    return value


class Option(BaseModel):
    """Une option de choix présentée dans un tool de réponse."""

    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=512)


__all__ = ["Option", "no_html"]
