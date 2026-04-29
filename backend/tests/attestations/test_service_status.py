"""F30 - Test du helper compute_status."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.attestations.service import compute_status


def test_status_active_when_valid_and_not_revoked() -> None:
    now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
    valid_until = now + timedelta(days=1)
    assert compute_status(valid_until=valid_until, revoked_at=None, now=now) == "active"


def test_status_expired_when_valid_until_past() -> None:
    now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
    valid_until = now - timedelta(seconds=1)
    assert (
        compute_status(valid_until=valid_until, revoked_at=None, now=now) == "expired"
    )


def test_status_revoked_takes_priority_over_expired() -> None:
    now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
    valid_until = now - timedelta(days=10)
    revoked_at = now - timedelta(days=5)
    assert (
        compute_status(valid_until=valid_until, revoked_at=revoked_at, now=now)
        == "revoked"
    )


def test_status_revoked_takes_priority_over_active() -> None:
    now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
    valid_until = now + timedelta(days=10)
    revoked_at = now - timedelta(seconds=5)
    assert (
        compute_status(valid_until=valid_until, revoked_at=revoked_at, now=now)
        == "revoked"
    )
