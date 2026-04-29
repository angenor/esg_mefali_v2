"""F03 US3 — Heuristiques de détection des affirmations ESG/financières.

Détecte les motifs `<chiffre>+<unité ESG>` (R6) ainsi que les mots-clés normatifs
(seuil, critère, formule, indicateur, référentiel, …).

Faux positif acceptable : un chiffre suivi d'une unité ESG sans contexte ESG
réel — la garde du middleware exige alors un cite_source.
Faux négatif inacceptable : un chiffre ESG omis qui ne déclenche pas la garde.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Unités ESG/financières ciblées (insensible à la casse)
_ESG_UNITS = (
    r"tCO2e?",
    r"kgCO2e?",
    r"FCFA",
    r"XOF",
    r"EUR",
    r"€",
    r"USD",
    r"\$",
    r"%",
    r"kWh",
    r"MWh",
    r"GWh",
    r"GJ",
    r"MJ",
    r"ha",  # hectares
    r"m3",  # mètres cubes
    r"litres?",
)
_UNITS_PATTERN = "|".join(_ESG_UNITS)

# Pattern : chiffre (entier ou décimal, séparateurs , ou .) suivi optionnellement
# d'un espace puis d'une unité ESG.
_NUMBER_UNIT_RE = re.compile(
    rf"\b\d+(?:[.,\s]\d+)*\s*({_UNITS_PATTERN})\b",
    flags=re.IGNORECASE,
)

# Mots-clés normatifs : leur seule présence avec une donnée chiffrée déclenche.
_NORMATIVE_KEYWORDS = re.compile(
    r"\b(?:seuil|crit[èe]re|formule|indicateur|"
    r"r[ée]f[ée]rentiel|facteur d'?[ée]mission|document requis)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class DetectionResult:
    has_esg_claim: bool
    detected_units: tuple[str, ...]
    keyword_hits: tuple[str, ...]


def detect_esg_claims(message: str) -> DetectionResult:
    """Détermine si ``message`` contient une affirmation ESG nécessitant un sourçage."""
    if not message:
        return DetectionResult(False, (), ())

    units = tuple(m.group(1) for m in _NUMBER_UNIT_RE.finditer(message))
    keywords = tuple(m.group(0).lower() for m in _NORMATIVE_KEYWORDS.finditer(message))

    has_claim = bool(units) or bool(keywords)
    return DetectionResult(
        has_esg_claim=has_claim,
        detected_units=units,
        keyword_hits=keywords,
    )
