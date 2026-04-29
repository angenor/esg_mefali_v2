"""F04 — Recompute happy path (T085, SC-003)."""

from __future__ import annotations

from datetime import UTC

import pytest

from app.snapshot.recompute import detect_drift, recompute_from_snapshot
from app.snapshot.schema import Money

pytestmark = pytest.mark.integration


def _build_snapshot(amount: str) -> dict:
    from datetime import datetime
    from uuid import uuid4

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


def test_recompute_immediately_after_submission_no_drift() -> None:
    snap = _build_snapshot("1234.56")
    money = recompute_from_snapshot(snap)
    assert detect_drift(snap, money) is False


def test_recompute_with_provider_drift_detected() -> None:
    snap = _build_snapshot("1000")

    def alt(parsed) -> Money:
        return Money(amount="1100", currency="XOF")

    money = recompute_from_snapshot(snap, score_provider=alt)
    assert detect_drift(snap, money) is True
