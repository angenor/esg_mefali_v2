"""F31 — Générateur déterministe de plans d'action ESG.

Transforme un ``ScoreCalculation.details_json`` en liste d'étapes priorisées.

Algorithme (cf. spec.md FR-007/FR-008 et research.md R-001/R-002) :

* extraction des lacunes via ``_extract_gaps`` (resilient sur format),
* mapping severity -> priority (haute/moyenne/basse),
* mapping pillar+code -> category (esg/carbone/credit/candidature),
* horizon_at = generated_at + offset_mois(priority, horizon_months),
* fallback "Revue annuelle ESG" si aucune lacune.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from app.action_plan.enums import Category, Priority
from app.action_plan.schemas import Gap

# --------------------------------------------------------------------------- #
#  Constantes algorithme                                                      #
# --------------------------------------------------------------------------- #

_HIGH_SEVERITY_THRESHOLD = Decimal("0.30")
_MID_SEVERITY_THRESHOLD = Decimal("0.60")

# Ordre d'affichage : priorité descendante → "haute" en tête.
_PRIORITY_ORDER: dict[Priority, int] = {
    Priority.HAUTE: 0,
    Priority.MOYENNE: 1,
    Priority.BASSE: 2,
}


@dataclass(frozen=True)
class StepDraft:
    """Étape proposée par le générateur — pré-persistance."""

    title: str
    description: str | None
    category: Category
    priority: Priority
    horizon_at: date
    indicateur_id: uuid.UUID | None
    source_id: uuid.UUID | None = None


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #


def _extract_gaps(details_json: dict[str, Any] | None) -> list[Gap]:
    """Extrait la liste des lacunes depuis ``details_json``.

    Tolérant : si ``details_json`` est ``None``, vide, ou n'a pas de ``gaps``,
    renvoie une liste vide sans lever.
    """
    if not details_json or not isinstance(details_json, dict):
        return []
    raw = details_json.get("gaps") or []
    if not isinstance(raw, list):
        return []

    gaps: list[Gap] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            ind_id_raw = item.get("indicator_id")
            ind_id = uuid.UUID(str(ind_id_raw)) if ind_id_raw else None
            score_raw = item.get("score_normalized", item.get("score", "1"))
            score = Decimal(str(score_raw))
            gap = Gap(
                indicator_id=ind_id,
                indicator_code=str(item.get("indicator_code") or "?"),
                indicator_label=str(item.get("indicator_label") or "indicateur ESG"),
                score_normalized=score,
                pillar=(str(item["pillar"]) if item.get("pillar") else None),
            )
            gaps.append(gap)
        except (ValueError, TypeError, KeyError, InvalidOperation):
            # ligne mal formée -> on l'ignore plutôt que faire planter le plan
            continue
    return gaps


def _severity_to_priority(score: Decimal) -> Priority:
    """Mappe un score normalisé [0..1] vers une priorité."""
    if score < _HIGH_SEVERITY_THRESHOLD:
        return Priority.HAUTE
    if score < _MID_SEVERITY_THRESHOLD:
        return Priority.MOYENNE
    return Priority.BASSE


def _priority_to_horizon_at(
    generated_at: datetime, horizon_months: int, priority: Priority
) -> date:
    """Calcule la date cible d'une étape selon sa priorité.

    haute → horizon/3, moyenne → horizon/2, basse → horizon complet.
    """
    if priority == Priority.HAUTE:
        offset_days = round(horizon_months * 30 / 3)
    elif priority == Priority.MOYENNE:
        offset_days = round(horizon_months * 30 / 2)
    else:
        offset_days = horizon_months * 30
    return (generated_at + timedelta(days=offset_days)).date()


def _pillar_to_category(pillar: str | None, indicator_code: str) -> Category:
    """Détermine la catégorie de l'étape.

    - pilier ``environnement`` + code contenant ``GES``/``CO2``/``EMI``/``SCOPE`` → carbone
    - sinon → esg
    """
    p = (pillar or "").strip().lower()
    code = (indicator_code or "").upper()
    is_emission_code = any(token in code for token in ("GES", "CO2", "EMI", "SCOPE"))
    if p in {"environnement", "environment", "e"} and is_emission_code:
        return Category.CARBONE
    return Category.ESG


def _build_default_step(
    generated_at: datetime, horizon_months: int
) -> StepDraft:
    """Étape par défaut quand aucune lacune n'est détectée (FR-008)."""
    horizon_at = (generated_at + timedelta(days=horizon_months * 30)).date()
    return StepDraft(
        title="Revue annuelle ESG",
        description=(
            "Aucune lacune ESG détectée par le dernier scoring. Maintenez une "
            "revue annuelle de vos indicateurs et politiques."
        ),
        category=Category.ESG,
        priority=Priority.MOYENNE,
        horizon_at=horizon_at,
        indicateur_id=None,
    )


def _build_step_from_gap(
    gap: Gap, generated_at: datetime, horizon_months: int
) -> StepDraft:
    priority = _severity_to_priority(gap.score_normalized)
    category = _pillar_to_category(gap.pillar, gap.indicator_code)
    horizon_at = _priority_to_horizon_at(generated_at, horizon_months, priority)
    title = f"Combler l'indicateur {gap.indicator_code} ({gap.indicator_label})"
    if len(title) > 200:
        title = title[:197] + "..."
    description = (
        f"Score actuel {gap.score_normalized}. Cible : amélioration progressive "
        f"avant {horizon_at.isoformat()}."
    )
    return StepDraft(
        title=title,
        description=description,
        category=category,
        priority=priority,
        horizon_at=horizon_at,
        indicateur_id=gap.indicator_id,
    )


def build_steps(
    details_json: dict[str, Any] | None,
    *,
    generated_at: datetime,
    horizon_months: int,
) -> list[StepDraft]:
    """Construit la liste ordonnée des étapes pour un plan.

    Tri stable : priorité (haute → basse), puis horizon_at, puis title.
    """
    gaps = _extract_gaps(details_json)
    drafts: list[StepDraft]
    if not gaps:
        drafts = [_build_default_step(generated_at, horizon_months)]
    else:
        drafts = [
            _build_step_from_gap(g, generated_at, horizon_months) for g in gaps
        ]

    drafts.sort(
        key=lambda d: (
            _PRIORITY_ORDER[d.priority],
            d.horizon_at,
            d.title,
        )
    )
    return drafts


__all__ = [
    "StepDraft",
    "build_steps",
    "_extract_gaps",
    "_severity_to_priority",
    "_priority_to_horizon_at",
    "_pillar_to_category",
]
