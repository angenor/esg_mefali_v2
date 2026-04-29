"""Tests unitaires pour `Money` (F05 — T012)."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.currencies import Currency
from app.schemas.money import Money


def test_money_create_valid() -> None:
    m = Money(amount=Decimal("1000"), currency=Currency.XOF)
    assert m.amount == Decimal("1000")
    assert m.currency is Currency.XOF


def test_money_rejects_unknown_currency() -> None:
    with pytest.raises(ValidationError):
        Money(amount=Decimal("10"), currency="ZZZ")  # type: ignore[arg-type]


def test_money_rejects_negative_amount() -> None:
    with pytest.raises(ValidationError):
        Money(amount=Decimal("-1"), currency=Currency.XOF)


def test_money_serializes_amount_as_string() -> None:
    m = Money(amount=Decimal("1000"), currency=Currency.XOF)
    payload = json.loads(m.model_dump_json())
    assert payload == {"amount": "1000", "currency": "XOF"}


def test_money_serializes_decimal_with_scale() -> None:
    m = Money(amount=Decimal("1000.50"), currency=Currency.EUR)
    payload = json.loads(m.model_dump_json())
    assert payload["amount"] == "1000.50"
    assert payload["currency"] == "EUR"


def test_money_is_frozen() -> None:
    m = Money(amount=Decimal("1"), currency=Currency.USD)
    with pytest.raises(ValidationError):
        m.amount = Decimal("2")  # type: ignore[misc]


def test_money_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Money(amount=Decimal("1"), currency=Currency.USD, extra="x")  # type: ignore[call-arg]
