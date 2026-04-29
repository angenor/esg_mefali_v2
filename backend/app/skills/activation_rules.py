"""F19 — Règles d'activation : Pydantic + matching contexte.

Schéma :
```json
{
  "any_of": [
    {"page": "/profil/projets/*", "intent": ["analyse","mutation"]},
    {"entity_type": "candidature",
     "offre_id_match": {"fonds_code": "GCF", "intermediaire_code": "BOAD"}}
  ]
}
```
"""

from __future__ import annotations

import fnmatch
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OffreMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fonds_code: str | None = None
    intermediaire_code: str | None = None


class Match(BaseModel):
    """Un critère de matching unique (tous les champs renseignés doivent matcher)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page: str | None = None
    intent: list[str] | None = None
    entity_type: str | None = None
    offre_id_match: OffreMatch | None = None


class ActivationRules(BaseModel):
    """`any_of` — au moins un Match doit matcher pour activer la skill."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    any_of: list[Match] = Field(default_factory=list)


def _match_one(rule: Match, context: dict[str, Any]) -> bool:
    """True si TOUS les champs renseignés de ``rule`` matchent ``context``."""
    if rule.page is not None:
        page = context.get("page")
        if not isinstance(page, str) or not fnmatch.fnmatchcase(page, rule.page):
            return False

    if rule.intent is not None:
        intent = context.get("intent")
        if intent not in rule.intent:
            return False

    if rule.entity_type is not None:
        if context.get("entity_type") != rule.entity_type:
            return False

    if rule.offre_id_match is not None:
        offre = context.get("offre") or {}
        if not isinstance(offre, dict):
            return False
        if rule.offre_id_match.fonds_code is not None:
            if offre.get("fonds_code") != rule.offre_id_match.fonds_code:
                return False
        if rule.offre_id_match.intermediaire_code is not None:
            if offre.get("intermediaire_code") != rule.offre_id_match.intermediaire_code:
                return False

    return True


def matches_context(rules: ActivationRules, context: dict[str, Any]) -> bool:
    """True si au moins un Match de ``any_of`` matche ``context``.

    Si ``any_of`` est vide → False (skill jamais activée par défaut).
    """
    if not rules.any_of:
        return False
    return any(_match_one(rule, context) for rule in rules.any_of)


def parse_rules(raw: dict[str, Any] | None) -> ActivationRules:
    """Parse un JSON brut → ActivationRules (vide si raw nul/falsy)."""
    if not raw:
        return ActivationRules()
    return ActivationRules.model_validate(raw)


__all__ = [
    "ActivationRules",
    "Match",
    "OffreMatch",
    "matches_context",
    "parse_rules",
]
