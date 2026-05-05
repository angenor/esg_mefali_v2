"""F48 - Mapping factor_name -> bucket sous-score.

Table déclarative pure-data utilisée par ``compute_subscores`` pour agréger
les ``facteurs`` retournés par ``CreditScoreOut`` en 4 sous-scores normalisés.

Un facteur non listé est silencieusement ignoré (dégradation gracieuse).
"""

from __future__ import annotations

from typing import Final

# Buckets canoniques exposés à l'UI (US2).
SUBSCORE_BUCKETS: Final[tuple[str, ...]] = (
    "solidite_financiere",
    "performance_operationnelle",
    "engagement_esg",
    "gouvernance",
)

# factor_name -> (bucket, weight_in_bucket)
# Les factor_name ci-dessous correspondent à la méthodologie par défaut
# F29 (cf. backend/app/credit/engine.py::DEFAULT_METHODOLOGY).
FACTOR_TO_BUCKET: Final[dict[str, tuple[str, float]]] = {
    # --- Solidité financière (Mobile Money + ancienneté + taille) ---
    "mm_volume": ("solidite_financiere", 0.35),
    "mm_regularite": ("solidite_financiere", 0.25),
    "entreprise_anciennete": ("solidite_financiere", 0.20),
    "entreprise_taille": ("solidite_financiere", 0.20),
    # --- Performance opérationnelle (paiements + diversification) ---
    "paiements_reguliers": ("performance_operationnelle", 0.50),
    "diversification_clients": ("performance_operationnelle", 0.50),
    # --- Engagement ESG (axe impact_vert) ---
    "esg_global": ("engagement_esg", 0.50),
    "carbone_intensite": ("engagement_esg", 0.30),
    "projets_verts": ("engagement_esg", 0.20),
    # --- Gouvernance (alignement ODD comme proxy initial) ---
    "alignement_odd": ("gouvernance", 1.00),
}
