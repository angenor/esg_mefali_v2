"""F25 — Heuristiques pures pour évaluer la compatibilité projet <-> offre.

Fonctions sans I/O ni DB, testables unitairement.

Conventions :
- Score d'une couche (fonds OU intermédiaire) = pourcentage [0..100] :
  - tout critère **blocking** non couvert ⇒ score=0,
  - sinon : (n_couverts / n_total) * 100. Si n_total=0, score=100.
- Money : conversion FCFA<->EUR via `PEG_FCFA_EUR` (655.957) du Module 0.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.currencies import PEG_FCFA_EUR, Currency
from app.matching.schemas import CritereMatch


def _to_eur(amount: Decimal | float | int | None, currency: str | None) -> Decimal | None:
    """Normalise un Money vers EUR (taux fixe FCFA-EUR 655.957)."""
    if amount is None or currency is None:
        return None
    amt = Decimal(str(amount))
    cur = currency.upper()
    if cur == Currency.EUR.value:
        return amt
    if cur == Currency.XOF.value:
        return (amt / PEG_FCFA_EUR).quantize(Decimal("0.0001"))
    return amt


def eval_money_range(
    *,
    projet_amount: Decimal | float | int | None,
    projet_currency: str | None,
    plancher: dict[str, Any] | None,
    plafond: dict[str, Any] | None,
) -> CritereMatch:
    """Vérifie que le montant projet est dans [plancher, plafond] du fonds."""
    label = "Montant dans la fourchette du fonds"
    if projet_amount is None or projet_currency is None:
        return CritereMatch(
            code="money_range",
            label=label,
            severity="blocking",
            covered=False,
            reason="value_missing",
        )

    p_eur = _to_eur(projet_amount, projet_currency)
    if p_eur is None:
        return CritereMatch(
            code="money_range",
            label=label,
            severity="blocking",
            covered=False,
            reason="conversion_failed",
        )

    if plancher:
        floor_eur = _to_eur(plancher.get("amount"), plancher.get("currency"))
        if floor_eur is not None and p_eur < floor_eur:
            return CritereMatch(
                code="money_range",
                label=label,
                severity="blocking",
                covered=False,
                reason="below_plancher",
            )
    if plafond:
        cap_eur = _to_eur(plafond.get("amount"), plafond.get("currency"))
        if cap_eur is not None and p_eur > cap_eur:
            return CritereMatch(
                code="money_range",
                label=label,
                severity="blocking",
                covered=False,
                reason="above_plafond",
            )
    return CritereMatch(
        code="money_range", label=label, severity="blocking", covered=True
    )


def eval_geo(
    *, projet_pays_iso2: str | None, eligibilite_geo: Iterable[str] | None
) -> CritereMatch:
    """Le pays du projet doit être dans la liste d'éligibilité géo."""
    label = "Pays éligible"
    if not eligibilite_geo:
        return CritereMatch(code="geo", label=label, severity="blocking", covered=True)
    if not projet_pays_iso2:
        return CritereMatch(
            code="geo",
            label=label,
            severity="blocking",
            covered=False,
            reason="value_missing",
        )
    eligibles = {x.upper() for x in eligibilite_geo if x}
    if projet_pays_iso2.upper() in eligibles:
        return CritereMatch(code="geo", label=label, severity="blocking", covered=True)
    return CritereMatch(
        code="geo",
        label=label,
        severity="blocking",
        covered=False,
        reason="not_in_list",
    )


def eval_thematique(
    *, projet_types_impact: Iterable[str] | None, fonds_thematique: Iterable[str] | None
) -> CritereMatch:
    """Au moins une thématique commune entre projet et fonds (warning)."""
    label = "Thématique compatible"
    if not fonds_thematique:
        return CritereMatch(
            code="thematique", label=label, severity="warning", covered=True
        )
    if not projet_types_impact:
        return CritereMatch(
            code="thematique",
            label=label,
            severity="warning",
            covered=False,
            reason="value_missing",
        )
    a = {x.lower() for x in projet_types_impact if x}
    b = {x.lower() for x in fonds_thematique if x}
    if a & b:
        return CritereMatch(
            code="thematique", label=label, severity="warning", covered=True
        )
    return CritereMatch(
        code="thematique",
        label=label,
        severity="warning",
        covered=False,
        reason="no_overlap",
    )


def eval_instruments(
    *,
    projet_structure: Iterable[str] | None,
    fonds_instruments: Iterable[str] | None,
) -> CritereMatch:
    """Instrument financier compatible (warning)."""
    label = "Instrument financier compatible"
    if not fonds_instruments:
        return CritereMatch(
            code="instruments", label=label, severity="warning", covered=True
        )
    if not projet_structure:
        return CritereMatch(
            code="instruments",
            label=label,
            severity="warning",
            covered=False,
            reason="value_missing",
        )
    a = {x.lower() for x in projet_structure if x}
    b = {x.lower() for x in fonds_instruments if x}
    if a & b:
        return CritereMatch(
            code="instruments", label=label, severity="warning", covered=True
        )
    return CritereMatch(
        code="instruments",
        label=label,
        severity="warning",
        covered=False,
        reason="no_overlap",
    )


def eval_critere_json(critere: dict[str, Any]) -> CritereMatch:
    """Évalue un critère libre stocké en JSONB.

    Schéma attendu : ``{code, label, severity, covered?, source_id?, reason?}``.
    Si ``covered`` est absent, on considère **non couvert** (MVP).
    """
    code = str(critere.get("code") or critere.get("id") or "critere")
    label = str(critere.get("label") or code)
    severity = str(critere.get("severity") or "warning").lower()
    if severity not in {"blocking", "warning"}:
        severity = "warning"
    covered = bool(critere.get("covered", False))
    source_raw = critere.get("source_id")
    source_id: UUID | None = None
    if source_raw:
        try:
            source_id = UUID(str(source_raw))
        except (ValueError, TypeError):
            source_id = None
    reason = critere.get("reason")
    if reason is None and not covered:
        reason = "not_evaluated"
    return CritereMatch(
        code=code,
        label=label,
        severity=severity,
        covered=covered,
        source_id=source_id,
        reason=str(reason) if reason else None,
    )


@dataclass(frozen=True)
class LayerScore:
    """Résultat de scoring d'une couche."""

    score: float
    couverts: list[CritereMatch]
    manquants: list[CritereMatch]


def score_layer(criteres: list[CritereMatch]) -> LayerScore:
    """Calcule un score 0..100 pour une couche de critères."""
    if not criteres:
        return LayerScore(score=100.0, couverts=[], manquants=[])
    couverts: list[CritereMatch] = []
    manquants: list[CritereMatch] = []
    blocking_missing = False
    for c in criteres:
        if c.covered:
            couverts.append(c)
        else:
            manquants.append(c)
            if c.severity == "blocking":
                blocking_missing = True
    if blocking_missing:
        return LayerScore(score=0.0, couverts=couverts, manquants=manquants)
    n_total = len(criteres)
    n_couverts = len(couverts)
    score = round((n_couverts / n_total) * 100, 2) if n_total else 100.0
    return LayerScore(score=score, couverts=couverts, manquants=manquants)
