"""Devises supportées et peg FCFA/EUR (F05 — US4/US5).

Le peg FCFA/EUR est une parité fixe officielle (BCEAO) — source : décret BCEAO.
Les autres devises (USD, GHS, NGN, MAD, GBP) sont snapshotées quotidiennement
via le job `refresh_fx_rates` (US5).
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

# Peg fixe FCFA/EUR (1 EUR = 655.957 XOF)
PEG_FCFA_EUR: Decimal = Decimal("655.957")


class Currency(StrEnum):
    """Devises supportées par la plateforme."""

    XOF = "XOF"
    EUR = "EUR"
    USD = "USD"
    GHS = "GHS"
    NGN = "NGN"
    MAD = "MAD"
    GBP = "GBP"


def inverse_peg() -> Decimal:
    """Retourne 1 / PEG_FCFA_EUR (XOF -> EUR), avec précision 12 décimales."""
    # Decimal division ; on garde 12 décimales pour stabilité d'affichage
    return (Decimal(1) / PEG_FCFA_EUR).quantize(Decimal("0.000000000001"))
