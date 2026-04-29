"""F27 - Primitives de calcul pures (sans DB) pour le simulateur.

Methodologie MVP documentee :
- Interets simples : I = P * (t/100) * (d/12)  (taux annuel %, duree en mois).
- Conversion XOF/EUR : peg fixe 655.957 (BCEAO). Autres devises non converties.
- Extraction de pourcentages tolerante : accepte str, float, int dans un dict JSON.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.currencies import PEG_FCFA_EUR, Currency
from app.schemas.money import Money

_TWO_PLACES = Decimal("0.01")


def convert_to_xof(money: Money) -> Money | None:
    """Convertit un Money en XOF.

    - XOF -> identique.
    - EUR -> multiplie par PEG_FCFA_EUR.
    - autre devise -> None (pas de FX disponible en MVP).
    """
    if money.currency == Currency.XOF:
        return money
    if money.currency == Currency.EUR:
        return Money(
            amount=(money.amount * PEG_FCFA_EUR).quantize(_TWO_PLACES),
            currency=Currency.XOF,
        )
    return None


def interets_simples(
    principal: Money, taux_pct_annuel: Decimal | None, duree_mois: int | None
) -> Money:
    """Calcule les interets simples cumules.

    Formule : I = P * (t/100) * (d/12).
    Retourne un Money de meme devise que le principal, arrondi 2 decimales.
    """
    if taux_pct_annuel is None or duree_mois is None or duree_mois <= 0:
        return Money(amount=Decimal("0.00"), currency=principal.currency)
    interest = (
        principal.amount
        * (taux_pct_annuel / Decimal(100))
        * (Decimal(duree_mois) / Decimal(12))
    ).quantize(_TWO_PLACES)
    return Money(amount=interest, currency=principal.currency)


def compute_pct_of(money: Money, pct: Decimal | None) -> Money | None:
    """Applique un pourcentage sur un Money. None si pct None."""
    if pct is None:
        return None
    out = (money.amount * pct / Decimal(100)).quantize(_TWO_PLACES)
    return Money(amount=out, currency=money.currency)


def extract_pct(payload: Any, *keys: str) -> Decimal | None:
    """Extrait un pourcentage Decimal depuis un dict JSON tolerant.

    Tente les cles dans l'ordre, retourne le premier match convertible en Decimal.
    Retourne None si payload n'est pas un dict, cles manquantes, ou valeur non numerique.
    """
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key not in payload:
            continue
        raw = payload[key]
        if raw is None:
            continue
        try:
            return Decimal(str(raw))
        except (InvalidOperation, ValueError):
            continue
    return None
