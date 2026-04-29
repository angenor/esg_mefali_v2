"""F28 - Moteur de calcul carbone (fonctions pures).

Conventions:
- ``factor_value`` est exprime en kgCO2e par unite physique (kWh, litre, km, kg).
- ``compute_line`` -> kgCO2e (Decimal).
- ``compute_total`` -> total kgCO2e + ventilation par scope (1, 2, 3).

Aucune IO. Aucune dependance SQLAlchemy.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

KG_PER_TONNE = Decimal("1000")


@dataclass(frozen=True)
class FactorRef:
    """Snapshot minimal d'un facteur F09 utilise pour un poste."""

    factor_id: str
    code: str
    valeur: Decimal
    unite: str
    scope: str  # "1" | "2" | "3"
    categorie: str
    source_id: str
    version: int


@dataclass(frozen=True)
class BreakdownLine:
    """Ligne de breakdown du calcul."""

    code: str
    quantity: Decimal
    unit: str
    factor: FactorRef
    kgco2e: Decimal


def compute_line(quantity: Decimal, factor: FactorRef) -> BreakdownLine:
    """Multiplie ``quantity`` par ``factor.valeur`` -> kgCO2e."""
    if quantity < 0:
        raise ValueError("quantity must be >= 0")
    kg = (Decimal(quantity) * factor.valeur).quantize(Decimal("0.000001"))
    return BreakdownLine(
        code=factor.code,
        quantity=Decimal(quantity),
        unit=factor.unite,
        factor=factor,
        kgco2e=kg,
    )


def compute_total(lines: Iterable[BreakdownLine]) -> dict[str, Decimal | dict[str, Decimal]]:
    """Somme totale + agregation par scope. Renvoie ``total_tco2e`` + ``by_scope``."""
    total_kg = Decimal("0")
    by_scope: dict[str, Decimal] = {"1": Decimal("0"), "2": Decimal("0"), "3": Decimal("0")}
    by_category: dict[str, Decimal] = {}
    for line in lines:
        total_kg += line.kgco2e
        scope = line.factor.scope if line.factor.scope in by_scope else "3"
        by_scope[scope] += line.kgco2e
        cat = line.factor.categorie or "autre"
        by_category[cat] = by_category.get(cat, Decimal("0")) + line.kgco2e
    return {
        "total_kgco2e": total_kg,
        "total_tco2e": (total_kg / KG_PER_TONNE).quantize(Decimal("0.000001")),
        "by_scope_kgco2e": by_scope,
        "by_category_kgco2e": by_category,
    }
