"""F23 — Scoring ESG multi-référentiels (MVP).

Moteur déterministe ``compute_score(...)`` calculant un score 0–100 sur la
base des indicateurs (F09) et des valeurs PME (F11). Aucune dépendance LLM.
Append-only via la table ``score_calculation``.
"""

from app.scoring.engine import (
    CoveredIndicator,
    IndicatorRule,
    MissingIndicator,
    ScoreResult,
    compute_score,
)

__all__ = [
    "CoveredIndicator",
    "IndicatorRule",
    "MissingIndicator",
    "ScoreResult",
    "compute_score",
]
