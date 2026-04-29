"""F04 — Recompute unit tests (T085-light, no DB)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.snapshot.recompute import detect_drift, recompute_from_snapshot
from app.snapshot.schema import Money


def _snap(amount: str = "100.00") -> dict:
    return {
        "schema_version": "1",
        "referentiel": {
            "logical_id": str(uuid4()),
            "version": 1,
            "valid_from": datetime.now(tz=UTC).isoformat(),
        },
        "offre": {"id": str(uuid4()), "criteres": []},
        "projet_state": {},
        "scores": {
            "global": {"amount": amount, "currency": "XOF"},
            "per_critere": {},
        },
        "sources": [],
    }


def test_recompute_default_returns_snapshotted_money() -> None:
    snap = _snap("250")
    money = recompute_from_snapshot(snap)
    assert money.amount == "250"
    assert money.currency == "XOF"


def test_no_drift_when_default_provider() -> None:
    snap = _snap("42")
    money = recompute_from_snapshot(snap)
    assert detect_drift(snap, money) is False


def test_drift_when_provider_returns_different_value() -> None:
    snap = _snap("100.00")

    def alt_scorer(parsed) -> Money:
        return Money(amount="105.00", currency="XOF")

    money = recompute_from_snapshot(snap, score_provider=alt_scorer)
    assert detect_drift(snap, money) is True


def test_provider_returning_decimal_uses_snapshot_currency() -> None:
    snap = _snap("0")
    money = recompute_from_snapshot(snap, score_provider=lambda p: Decimal("7.5"))
    assert money == Money(amount="7.5", currency="XOF")


def test_provider_unsupported_type_raises() -> None:
    with pytest.raises(TypeError):
        recompute_from_snapshot(_snap(), score_provider=lambda p: object())
