"""F29 - Credit scoring engine (fonctions pures, pas de DB).

Algorithme MVP : regles ponderees sourcees (cf plan.md Phase 1).

3 scores :
- ``solvabilite`` : combine indicateurs Mobile Money + ancienete + taille +
  paiements + diversification.
- ``impact_vert`` : combine score ESG + intensite carbone + projets verts +
  alignement ODD.
- ``combine`` = round(alpha * solvabilite + beta * impact_vert).

Si une source de donnees est absente, le facteur est garde avec
``value=null, contribution=0`` ; ``coherence_warning=true`` lorsque la
couverture (somme des poids des facteurs disponibles) tombe sous 50% pour
solvabilite ou impact_vert, ou lorsque ``combine > 80`` sans Mobile Money
ni ESG (sentinelle anti-usurpation).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FactorDef:
    """Definition d'un facteur dans la methodologie."""

    name: str
    definition: str
    weight: float
    source_id: str
    axis: str  # "solvabilite" | "impact_vert"


@dataclass(frozen=True)
class FactorResult:
    """Facteur calcule pour une PME donnee."""

    name: str
    definition: str
    value: float | None
    weight: float
    contribution: float
    source_id: str
    axis: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "definition": self.definition,
            "value": self.value,
            "weight": self.weight,
            "contribution": self.contribution,
            "source_id": self.source_id,
            "axis": self.axis,
        }


# --------------------------------------------------------------------------- #
# Helpers de normalisation                                                    #
# --------------------------------------------------------------------------- #


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _normalize_log(n: float | None, base: int = 101) -> float | None:
    if n is None or n < 0:
        return None
    return _clamp(math.log(n + 1) / math.log(base))


def _normalize_anciennete(years: float | None, max_years: float = 10) -> float | None:
    if years is None or years < 0:
        return None
    return _clamp(years / max_years)


def _normalize_volume_xof(volume: float | None) -> float | None:
    if volume is None or volume < 0:
        return None
    return _clamp(volume / 1_000_000)


def _normalize_regularite(mean: float | None, stdev: float | None) -> float | None:
    if mean is None or stdev is None or mean <= 0 or stdev < 0:
        return None
    return _clamp(1 - (stdev / mean))


def _normalize_carbone(total_tco2e: float | None) -> float | None:
    if total_tco2e is None or total_tco2e < 0:
        return None
    return _clamp(1 - min(total_tco2e / 1000, 1.0))


# --------------------------------------------------------------------------- #
# Calcul d'un facteur                                                         #
# --------------------------------------------------------------------------- #


def compute_factor(
    definition: FactorDef, normalized_value: float | None
) -> FactorResult:
    if normalized_value is None:
        return FactorResult(
            name=definition.name,
            definition=definition.definition,
            value=None,
            weight=definition.weight,
            contribution=0.0,
            source_id=definition.source_id,
            axis=definition.axis,
        )
    return FactorResult(
        name=definition.name,
        definition=definition.definition,
        value=round(normalized_value, 4),
        weight=definition.weight,
        contribution=round(normalized_value * definition.weight, 4),
        source_id=definition.source_id,
        axis=definition.axis,
    )


# --------------------------------------------------------------------------- #
# Scores agreges                                                              #
# --------------------------------------------------------------------------- #


def _score_axis(factors: list[FactorResult], axis: str) -> int:
    contrib_sum = sum(f.contribution for f in factors if f.axis == axis)
    return int(round(_clamp(contrib_sum) * 100))


def axis_coverage(factors: list[FactorResult], axis: str) -> float:
    total = sum(f.weight for f in factors if f.axis == axis)
    if total <= 0:
        return 0.0
    available = sum(
        f.weight for f in factors if f.axis == axis and f.value is not None
    )
    return available / total


def compute_solvabilite(factors: list[FactorResult]) -> int:
    return _score_axis(factors, "solvabilite")


def compute_impact_vert(factors: list[FactorResult]) -> int:
    return _score_axis(factors, "impact_vert")


def compute_combined(
    solvabilite: int, impact_vert: int, alpha: float = 0.6, beta: float = 0.4
) -> int:
    if not (0.0 <= alpha <= 1.0 and 0.0 <= beta <= 1.0):
        raise ValueError("alpha et beta doivent etre dans [0,1]")
    if abs(alpha + beta - 1.0) > 1e-6:
        raise ValueError("alpha + beta doit valoir 1")
    return int(round(alpha * solvabilite + beta * impact_vert))


def has_mobile_money(factors: list[FactorResult]) -> bool:
    return any(f.name.startswith("mm_") and f.value is not None for f in factors)


def has_esg(factors: list[FactorResult]) -> bool:
    return any(f.name == "esg_global" and f.value is not None for f in factors)


def coherence_warning(
    factors: list[FactorResult],
    combine: int,
    *,
    coverage_threshold: float = 0.5,
) -> bool:
    cov_solv = axis_coverage(factors, "solvabilite")
    cov_imp = axis_coverage(factors, "impact_vert")
    if cov_solv < coverage_threshold or cov_imp < coverage_threshold:
        return True
    if combine > 80 and not (has_mobile_money(factors) or has_esg(factors)):
        return True
    return False


# --------------------------------------------------------------------------- #
# Methodologie par defaut (fallback si seed absent)                           #
# --------------------------------------------------------------------------- #


DEFAULT_METHODOLOGY: dict[str, Any] = {
    "version": 1,
    "alpha": 0.6,
    "beta": 0.4,
    "factors": [
        {
            "name": "mm_volume",
            "axis": "solvabilite",
            "weight": 0.25,
            "definition": "Volume mensuel moyen Mobile Money normalise sur 1 000 000 XOF.",
        },
        {
            "name": "mm_regularite",
            "axis": "solvabilite",
            "weight": 0.20,
            "definition": "1 - (ecart-type / moyenne) des volumes mensuels Mobile Money.",
        },
        {
            "name": "entreprise_anciennete",
            "axis": "solvabilite",
            "weight": 0.15,
            "definition": "Annees depuis la creation de l'entreprise / 10, capee a 1.",
        },
        {
            "name": "entreprise_taille",
            "axis": "solvabilite",
            "weight": 0.10,
            "definition": "log(employes+1) / log(101), capee a 1.",
        },
        {
            "name": "paiements_reguliers",
            "axis": "solvabilite",
            "weight": 0.15,
            "definition": "1.0 si paiements fournisseurs/employes reguliers declares, 0.5 sinon.",
        },
        {
            "name": "diversification_clients",
            "axis": "solvabilite",
            "weight": 0.15,
            "definition": "min(nb_clients_recurrents / 10, 1.0).",
        },
        {
            "name": "esg_global",
            "axis": "impact_vert",
            "weight": 0.40,
            "definition": "Score ESG global (F23) du dernier calcul / 100.",
        },
        {
            "name": "carbone_intensite",
            "axis": "impact_vert",
            "weight": 0.30,
            "definition": "1 - min(total_tco2e / 1000, 1.0) (F28).",
        },
        {
            "name": "projets_verts",
            "axis": "impact_vert",
            "weight": 0.20,
            "definition": "min(nb_projets_verts / 3, 1.0).",
        },
        {
            "name": "alignement_odd",
            "axis": "impact_vert",
            "weight": 0.10,
            "definition": "min(nb_odd_alignes / 5, 1.0).",
        },
    ],
}


# --------------------------------------------------------------------------- #
# Calcul complet a partir des donnees brutes                                  #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ScoringInputs:
    """Donnees brutes consommees par l'engine."""

    mm_monthly_mean_xof: float | None = None
    mm_monthly_stdev_xof: float | None = None
    entreprise_anciennete_years: float | None = None
    entreprise_employes: float | None = None
    paiements_reguliers: bool | None = None
    diversification_clients: int | None = None
    esg_score_global: float | None = None
    carbone_total_tco2e: float | None = None
    nb_projets_verts: int | None = None
    nb_odd_alignes: int | None = None


def _factor_def(spec: dict[str, Any], source_map: dict[str, str]) -> FactorDef:
    return FactorDef(
        name=spec["name"],
        definition=spec["definition"],
        weight=float(spec["weight"]),
        source_id=source_map.get(spec["name"], "unsourced"),
        axis=spec["axis"],
    )


def compute_factors_from_inputs(
    inputs: ScoringInputs,
    methodology: dict[str, Any] | None = None,
    source_map: dict[str, str] | None = None,
) -> list[FactorResult]:
    methodology = methodology or DEFAULT_METHODOLOGY
    source_map = source_map or {
        spec["name"]: "unsourced" for spec in methodology["factors"]
    }
    out: list[FactorResult] = []
    for spec in methodology["factors"]:
        defn = _factor_def(spec, source_map)
        name = spec["name"]
        normalized: float | None
        if name == "mm_volume":
            normalized = _normalize_volume_xof(inputs.mm_monthly_mean_xof)
        elif name == "mm_regularite":
            normalized = _normalize_regularite(
                inputs.mm_monthly_mean_xof, inputs.mm_monthly_stdev_xof
            )
        elif name == "entreprise_anciennete":
            normalized = _normalize_anciennete(inputs.entreprise_anciennete_years)
        elif name == "entreprise_taille":
            normalized = _normalize_log(inputs.entreprise_employes)
        elif name == "paiements_reguliers":
            if inputs.paiements_reguliers is None:
                normalized = None
            else:
                normalized = 1.0 if inputs.paiements_reguliers else 0.5
        elif name == "diversification_clients":
            if inputs.diversification_clients is None:
                normalized = None
            else:
                normalized = _clamp(inputs.diversification_clients / 10.0)
        elif name == "esg_global":
            if inputs.esg_score_global is None:
                normalized = None
            else:
                normalized = _clamp(inputs.esg_score_global / 100.0)
        elif name == "carbone_intensite":
            normalized = _normalize_carbone(inputs.carbone_total_tco2e)
        elif name == "projets_verts":
            if inputs.nb_projets_verts is None:
                normalized = None
            else:
                normalized = _clamp(inputs.nb_projets_verts / 3.0)
        elif name == "alignement_odd":
            if inputs.nb_odd_alignes is None:
                normalized = None
            else:
                normalized = _clamp(inputs.nb_odd_alignes / 5.0)
        else:
            normalized = None
        out.append(compute_factor(defn, normalized))
    return out


def compute_full_score(
    inputs: ScoringInputs,
    methodology: dict[str, Any] | None = None,
    source_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    methodology = methodology or DEFAULT_METHODOLOGY
    factors = compute_factors_from_inputs(inputs, methodology, source_map)
    solv = compute_solvabilite(factors)
    imp = compute_impact_vert(factors)
    alpha = float(methodology.get("alpha", 0.6))
    beta = float(methodology.get("beta", 0.4))
    combine = compute_combined(solv, imp, alpha=alpha, beta=beta)
    warning = coherence_warning(factors, combine)
    return {
        "solvabilite": solv,
        "impact_vert": imp,
        "combine": combine,
        "facteurs": [f.to_dict() for f in factors],
        "methodologie_version": int(methodology.get("version", 1)),
        "coherence_warning": warning,
    }
