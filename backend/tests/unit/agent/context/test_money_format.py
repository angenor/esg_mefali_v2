"""F54 / T015 — Tests unitaires money_format (NFR-006).

Couvre :
- Affichage XOF seul (pas d'équivalent).
- Mix XOF/EUR : affichage devise native + équivalent XOF entre parenthèses.
- Mix XOF/USD : conversion via fx_rate snapshot.
- Peg fixe FCFA-EUR 655.957.
- None / amount nul.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.agent.context.money_format import (
    FX_PEG_XOF_EUR,
    Money,
    collect_currencies,
    format_money,
)


@pytest.mark.unit
class TestPegConstant:
    def test_peg_is_655_957(self) -> None:
        # P5 — peg fixe officiel UEMOA.
        assert FX_PEG_XOF_EUR == Decimal("655.957")


@pytest.mark.unit
class TestFormatMoneySingleCurrency:
    """Cas mono-devise : pas d'équivalent affiché (NFR-006 spec)."""

    def test_xof_only_no_equivalent(self) -> None:
        m = Money(amount=Decimal("15000000"), currency="XOF")
        s = format_money(m, native_currencies={"XOF"})
        assert "XOF" in s
        assert "15" in s
        # Pas de parenthèses d'équivalent.
        assert "(" not in s

    def test_eur_only_no_equivalent(self) -> None:
        m = Money(amount=Decimal("22000"), currency="EUR")
        s = format_money(m, native_currencies={"EUR"})
        assert "EUR" in s
        assert "(" not in s

    def test_usd_only_no_equivalent(self) -> None:
        m = Money(amount=Decimal("100"), currency="USD")
        s = format_money(m, native_currencies={"USD"})
        assert "USD" in s
        assert "(" not in s


@pytest.mark.unit
class TestFormatMoneyMultiCurrencyPeg:
    """Cas multi-devise : équivalent XOF affiché (sauf si déjà XOF)."""

    def test_xof_with_eur_present_no_equivalent_self(self) -> None:
        # XOF reste XOF même si EUR aussi présent — pas de tautologie.
        m = Money(amount=Decimal("15000000"), currency="XOF")
        s = format_money(m, native_currencies={"XOF", "EUR"})
        # XOF ne se convertit pas en lui-même.
        assert "(" not in s

    def test_eur_with_xof_present_shows_xof_equivalent(self) -> None:
        m = Money(amount=Decimal("100"), currency="EUR")
        s = format_money(m, native_currencies={"XOF", "EUR"})
        # 100 EUR × 655.957 = 65 595.7 XOF → arrondi HALF_UP → 65 596.
        assert "EUR" in s
        assert "XOF" in s
        # Le formatage utilise un espace comme séparateur de milliers.
        assert "65 596" in s

    def test_eur_to_xof_uses_peg(self) -> None:
        # 1 EUR = 655.957 XOF strict.
        m = Money(amount=Decimal("1"), currency="EUR")
        s = format_money(m, native_currencies={"XOF", "EUR"})
        assert "656" in s or "655" in s  # arrondi selon stratégie.


@pytest.mark.unit
class TestFormatMoneyMultiCurrencyUSD:
    """Cas USD : conversion via ``fx_rate_usd_to_xof`` quand fourni."""

    def test_usd_to_xof_with_fx_rate(self) -> None:
        m = Money(amount=Decimal("10"), currency="USD")
        # Suppose 1 USD = 600 XOF (snapshot fictif).
        s = format_money(
            m,
            native_currencies={"XOF", "USD"},
            fx_rate_usd_to_xof=Decimal("600"),
        )
        assert "USD" in s
        assert "XOF" in s
        # 10 × 600 = 6000.
        assert "6" in s and "000" in s

    def test_usd_without_fx_rate_no_equivalent(self) -> None:
        m = Money(amount=Decimal("10"), currency="USD")
        # Pas de fx_rate fourni → pas d'équivalent (soft-fail).
        s = format_money(
            m,
            native_currencies={"XOF", "USD"},
            fx_rate_usd_to_xof=None,
        )
        assert "USD" in s
        # Pas d'équivalent puisqu'on n'a pas de taux.
        assert "(" not in s


@pytest.mark.unit
class TestFormatMoneyEdgeCases:
    def test_zero_amount(self) -> None:
        m = Money(amount=Decimal("0"), currency="XOF")
        s = format_money(m, native_currencies={"XOF"})
        assert "0" in s

    def test_decimal_with_cents(self) -> None:
        m = Money(amount=Decimal("1234.56"), currency="EUR")
        s = format_money(m, native_currencies={"EUR"})
        # On affiche le montant tel quel ou arrondi sain.
        assert "1" in s and "234" in s


@pytest.mark.unit
class TestCollectCurrencies:
    def test_empty(self) -> None:
        assert collect_currencies([]) == set()

    def test_single(self) -> None:
        m = Money(amount=Decimal("100"), currency="XOF")
        assert collect_currencies([m]) == {"XOF"}

    def test_multi(self) -> None:
        a = Money(amount=Decimal("100"), currency="XOF")
        b = Money(amount=Decimal("10"), currency="EUR")
        assert collect_currencies([a, b]) == {"XOF", "EUR"}

    def test_ignores_none(self) -> None:
        a = Money(amount=Decimal("100"), currency="XOF")
        assert collect_currencies([a, None]) == {"XOF"}
