"""F55 / T081 — Unit tests confirmation flow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.agent.confirmation import (
    build_pending_confirmation,
    is_expired,
)
from app.agent.state import PendingConfirmation

pytestmark = pytest.mark.unit


def test_build_pending_confirmation_default_ttl():
    pending = build_pending_confirmation(
        tool_call_id="call_1",
        tool_name="delete_project",
        arguments={"projet_id": "abc"},
        ttl_seconds=180,
    )
    assert pending.tool_call_id == "call_1"
    assert pending.tool_name == "delete_project"
    assert pending.expires_at > datetime.now(UTC)
    assert pending.expires_at <= datetime.now(UTC) + timedelta(seconds=200)


def test_is_expired_true_after_ttl():
    pending = PendingConfirmation(
        tool_call_id="x",
        tool_name="delete_project",
        arguments={},
        expires_at=datetime.now(UTC) - timedelta(seconds=10),
    )
    assert is_expired(pending) is True


def test_is_expired_false_before_ttl():
    pending = PendingConfirmation(
        tool_call_id="x",
        tool_name="delete_project",
        arguments={},
        expires_at=datetime.now(UTC) + timedelta(seconds=60),
    )
    assert is_expired(pending) is False


def test_is_expired_naive_datetime_treated_as_utc():
    pending = PendingConfirmation(
        tool_call_id="x",
        tool_name="delete_project",
        arguments={},
        expires_at=datetime(1990, 1, 1),  # naive past datetime
    )
    assert is_expired(pending) is True


def test_pending_confirmation_strict_extra_forbid():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PendingConfirmation(
            tool_call_id="x",
            tool_name="y",
            arguments={},
            expires_at=datetime.now(UTC),
            extra_field="forbidden",  # type: ignore[call-arg]
        )
