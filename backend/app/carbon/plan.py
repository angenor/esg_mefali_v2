"""F28 - Plan de reduction carbone (stub MVP).

Bibliotheque inline d'actions priorisees. La table ``action_reduction`` seedee
est ``[DEFERRED]``. Le service expose ``generate_plan(by_category)`` qui filtre
les actions pertinentes selon les contributeurs majeurs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ReductionAction:
    code: str
    category: str  # energie | transport | dechets
    scope: str  # "1" | "2" | "3"
    horizon: str  # quick_win | medium | long
    description: str
    impact_kgco2e_year: Decimal


# Bibliotheque MVP : 5 actions couvrant energie/transport/dechets, 3 horizons.
LIBRARY: tuple[ReductionAction, ...] = (
    ReductionAction(
        code="LED_RETROFIT",
        category="energie",
        scope="2",
        horizon="quick_win",
        description="Remplacer eclairage par LED basse consommation.",
        impact_kgco2e_year=Decimal("450"),
    ),
    ReductionAction(
        code="GENERATEUR_OPTIMISATION",
        category="energie",
        scope="1",
        horizon="quick_win",
        description="Reduire usage du generateur diesel via planification charges.",
        impact_kgco2e_year=Decimal("1200"),
    ),
    ReductionAction(
        code="FLEET_ECO_DRIVING",
        category="transport",
        scope="1",
        horizon="quick_win",
        description="Formation eco-conduite + suivi consommation flotte.",
        impact_kgco2e_year=Decimal("300"),
    ),
    ReductionAction(
        code="SOLAR_PV_INSTALL",
        category="energie",
        scope="2",
        horizon="long",
        description="Installer panneaux solaires PV pour autoconsommation.",
        impact_kgco2e_year=Decimal("3500"),
    ),
    ReductionAction(
        code="TRI_DECHETS",
        category="dechets",
        scope="3",
        horizon="medium",
        description="Mettre en place tri et collecte selective des dechets.",
        impact_kgco2e_year=Decimal("200"),
    ),
)


def generate_plan(
    by_category_kgco2e: Mapping[str, Decimal],
    *,
    max_actions: int = 5,
) -> list[dict]:
    """Renvoie la liste d'actions priorisees par impact decroissant."""
    relevant_categories = set(by_category_kgco2e.keys())
    if relevant_categories:
        actions = [a for a in LIBRARY if a.category in relevant_categories]
        if not actions:
            actions = list(LIBRARY)
    else:
        actions = list(LIBRARY)
    actions = sorted(actions, key=lambda a: a.impact_kgco2e_year, reverse=True)
    return [asdict(a) for a in actions[:max_actions]]
