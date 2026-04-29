"""F11 — Indicateur de complétude du profil entreprise.

Matrice features→champs requis déclarative. Évoluer F23/F29 ne casse pas F11.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

GLOBAL_FIELDS: tuple[str, ...] = (
    "name",
    "secteur_code",
    "taille_ca",
    "taille_effectifs",
    "localisation_siege_pays_iso2",
    "localisation_siege_ville",
    "zones_operation_pays_iso2",
    "gouvernance_json",
    "pratiques_actuelles_json",
)


@dataclass(frozen=True)
class FeatureRequirement:
    feature_code: str
    required_fields: tuple[str, ...]


FEATURE_REQUIREMENTS: tuple[FeatureRequirement, ...] = (
    FeatureRequirement(
        feature_code="esg_scoring",
        required_fields=("secteur_code", "taille_effectifs", "taille_ca"),
    ),
    FeatureRequirement(
        feature_code="credit_scoring",
        required_fields=(
            "secteur_code",
            "taille_ca",
            "taille_effectifs",
            "localisation_siege_pays_iso2",
        ),
    ),
    FeatureRequirement(
        feature_code="matching_offre",
        required_fields=(
            "secteur_code",
            "localisation_siege_pays_iso2",
            "zones_operation_pays_iso2",
        ),
    ),
)


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def compute_percentage(profile: dict[str, Any]) -> int:
    if not GLOBAL_FIELDS:
        return 100
    filled = sum(1 for f in GLOBAL_FIELDS if _is_filled(profile.get(f)))
    return int(round(100 * filled / len(GLOBAL_FIELDS)))


def compute_missing_per_feature(profile: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for req in FEATURE_REQUIREMENTS:
        missing = [f for f in req.required_fields if not _is_filled(profile.get(f))]
        results.append({"feature_code": req.feature_code, "missing_fields": missing})
    return results
