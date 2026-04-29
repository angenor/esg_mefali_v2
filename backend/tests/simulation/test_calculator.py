"""F27 - Tests unitaires des primitives de calcul (sans DB)."""

from __future__ import annotations

from decimal import Decimal

from app.core.currencies import PEG_FCFA_EUR, Currency
from app.schemas.money import Money
from app.simulation.calculator import (
    compute_pct_of,
    convert_to_xof,
    extract_pct,
    interets_simples,
)


def test_convert_to_xof_xof_identity():
    m = Money(amount=Decimal("1000000"), currency=Currency.XOF)
    out = convert_to_xof(m)
    assert out == m


def test_convert_to_xof_eur_via_peg():
    m = Money(amount=Decimal("1000"), currency=Currency.EUR)
    out = convert_to_xof(m)
    assert out is not None
    assert out.currency == Currency.XOF
    assert out.amount == (Decimal("1000") * PEG_FCFA_EUR).quantize(Decimal("0.01"))


def test_convert_to_xof_usd_unsupported():
    m = Money(amount=Decimal("1000"), currency=Currency.USD)
    assert convert_to_xof(m) is None


def test_interets_simples_zero_taux():
    out = interets_simples(
        Money(amount=Decimal("100000"), currency=Currency.EUR),
        Decimal("0"),
        duree_mois=12,
    )
    assert out.amount == Decimal("0.00")


def test_interets_simples_correct():
    out = interets_simples(
        Money(amount=Decimal("100000"), currency=Currency.EUR),
        Decimal("4"),
        duree_mois=84,
    )
    assert out.currency == Currency.EUR
    assert out.amount == Decimal("28000.00")


def test_interets_simples_partial_year():
    out = interets_simples(
        Money(amount=Decimal("100000"), currency=Currency.EUR),
        Decimal("5"),
        duree_mois=6,
    )
    assert out.amount == Decimal("2500.00")


def test_compute_pct_of_basic():
    m = Money(amount=Decimal("100000"), currency=Currency.EUR)
    out = compute_pct_of(m, Decimal("2"))
    assert out is not None
    assert out.amount == Decimal("2000.00")
    assert out.currency == Currency.EUR


def test_compute_pct_of_none():
    m = Money(amount=Decimal("100000"), currency=Currency.EUR)
    assert compute_pct_of(m, None) is None


def test_extract_pct_present():
    j = {"frais_dossier_pct": "1.5"}
    assert extract_pct(j, "frais_dossier_pct") == Decimal("1.5")


def test_extract_pct_fallback_keys():
    j = {"marge_pct": "2"}
    assert extract_pct(j, "marge_intermediaire_pct", "marge_pct") == Decimal("2")


def test_extract_pct_missing():
    assert extract_pct({}, "nope") is None
    assert extract_pct(None, "nope") is None
    assert extract_pct({"x": "abc"}, "x") is None


def test_extract_pct_numeric():
    assert extract_pct({"x": 3.5}, "x") == Decimal("3.5")
    assert extract_pct({"x": 4}, "x") == Decimal("4")
