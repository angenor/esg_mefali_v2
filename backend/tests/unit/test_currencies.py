"""Tests pour `app.core.currencies` (F05 — T005 support)."""

from __future__ import annotations

from decimal import Decimal

from app.core.currencies import PEG_FCFA_EUR, Currency, inverse_peg


def test_currency_enum_has_seven_supported_currencies() -> None:
    expected = {"XOF", "EUR", "USD", "GHS", "NGN", "MAD", "GBP"}
    assert {c.value for c in Currency} == expected


def test_peg_fcfa_eur_constant() -> None:
    assert PEG_FCFA_EUR == Decimal("655.957")


def test_inverse_peg_round_trip() -> None:
    inv = inverse_peg()
    # 1 EUR = 655.957 XOF, donc inverse_peg() ≈ 0.001524..., et le produit ≈ 1
    product = (inv * PEG_FCFA_EUR).quantize(Decimal("0.0000001"))
    assert product == Decimal("1.0000000")
