"""F23 — Moteur de scoring weighted_sum (MVP).

Calcule un score 0-100 par référentiel à partir d'une liste d'indicateurs
typés et de leurs poids, en appliquant la normalisation (mod normalizer)
puis une somme pondérée renormalisée sur les indicateurs effectivement
couverts.

Invariants :
- Déterministe : mêmes inputs ⇒ même score.
- Coverage partielle : seuls les indicateurs couverts contribuent.
- ``score_global = None`` si aucun indicateur couvert ou ``sum(weights) = 0``.
- ``scores_by_pillar.X = None`` si aucun indicateur couvert sur le pilier X.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.scoring.normalizer import normalize_value


@dataclass(frozen=True)
class IndicatorRule:
    """Règle de calcul pour un indicateur d'un référentiel."""

    indicateur_id: uuid.UUID
    indicateur_code: str
    pillar: str
    value_type: str
    weight: float
    source_id: uuid.UUID | None
    seuil_min: Any = None
    seuil_max: Any = None
    enum_values: list[Any] | None = None


@dataclass(frozen=True)
class CoveredIndicator:
    indicateur_id: uuid.UUID
    indicateur_code: str
    pillar: str
    value: Any
    normalized_value: float
    weight: float
    contribution: float
    source_id: uuid.UUID


@dataclass(frozen=True)
class MissingIndicator:
    indicateur_id: uuid.UUID
    indicateur_code: str
    pillar: str
    reason: str


@dataclass(frozen=True)
class ScoreResult:
    score_global: float | None
    scores_by_pillar: dict[str, float | None]
    coverage_ratio: float | None
    indicateurs_couverts: list[CoveredIndicator] = field(default_factory=list)
    indicateurs_manquants: list[MissingIndicator] = field(default_factory=list)
    sources_used: list[uuid.UUID] = field(default_factory=list)


def _round(v: float, digits: int = 4) -> float:
    return round(v, digits)


def compute_score(
    *,
    rules: list[IndicatorRule],
    values: dict[str, Any],
) -> ScoreResult:
    """Calcule un score weighted_sum pour un référentiel donné."""
    covered: list[CoveredIndicator] = []
    missing: list[MissingIndicator] = []
    pillar_buckets: dict[str, list[tuple[float, float]]] = {}

    for rule in rules:
        if rule.source_id is None:
            missing.append(
                MissingIndicator(
                    indicateur_id=rule.indicateur_id,
                    indicateur_code=rule.indicateur_code,
                    pillar=rule.pillar,
                    reason="referentiel_indicateur_misconfig",
                )
            )
            continue

        raw = values.get(rule.indicateur_code)
        norm = normalize_value(
            value=raw,
            value_type=rule.value_type,
            seuil_min=rule.seuil_min,
            seuil_max=rule.seuil_max,
            enum_values=rule.enum_values,
        )

        if not norm.is_covered:
            missing.append(
                MissingIndicator(
                    indicateur_id=rule.indicateur_id,
                    indicateur_code=rule.indicateur_code,
                    pillar=rule.pillar,
                    reason=norm.reason or "value_absent",
                )
            )
            continue

        weight = float(rule.weight)
        if weight <= 0:
            covered.append(
                CoveredIndicator(
                    indicateur_id=rule.indicateur_id,
                    indicateur_code=rule.indicateur_code,
                    pillar=rule.pillar,
                    value=raw,
                    normalized_value=_round(norm.value or 0.0),
                    weight=weight,
                    contribution=0.0,
                    source_id=rule.source_id,
                )
            )
            continue

        normalized = norm.value or 0.0
        contribution = weight * normalized
        covered.append(
            CoveredIndicator(
                indicateur_id=rule.indicateur_id,
                indicateur_code=rule.indicateur_code,
                pillar=rule.pillar,
                value=raw,
                normalized_value=_round(normalized),
                weight=weight,
                contribution=_round(contribution),
                source_id=rule.source_id,
            )
        )
        pillar_buckets.setdefault(rule.pillar, []).append((weight, normalized))

    contributing = [(c.weight, c.normalized_value) for c in covered if c.weight > 0]
    total_weight = sum(w for w, _ in contributing)
    score_global: float | None = (
        _round(sum(w * v for w, v in contributing) / total_weight, 2)
        if total_weight > 0
        else None
    )

    pillar_scores: dict[str, float | None] = {}
    for pillar, items in pillar_buckets.items():
        contributing_p = [(w, v) for w, v in items if w > 0]
        tw = sum(w for w, _ in contributing_p)
        pillar_scores[pillar] = (
            _round(sum(w * v for w, v in contributing_p) / tw, 2) if tw > 0 else None
        )

    declared_total = sum(
        float(r.weight) for r in rules if r.source_id is not None and float(r.weight) > 0
    )
    coverage_ratio: float | None = (
        _round(total_weight / declared_total, 4) if declared_total > 0 else None
    )

    sources = sorted({c.source_id for c in covered}, key=str)

    return ScoreResult(
        score_global=score_global,
        scores_by_pillar=pillar_scores,
        coverage_ratio=coverage_ratio,
        indicateurs_couverts=covered,
        indicateurs_manquants=missing,
        sources_used=sources,
    )
