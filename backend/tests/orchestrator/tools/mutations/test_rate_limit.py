"""F17 — Tests décorateur ``@rate_limited`` (FR-010)."""

from __future__ import annotations

import time

import pytest

from app.orchestrator.tools.mutations._rate_limit import (
    RateLimitExceeded,
    rate_limited,
    reset_rate_limit_state,
)


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    reset_rate_limit_state()
    yield
    reset_rate_limit_state()


def test_allows_under_limit() -> None:
    @rate_limited(max_per_min=3)
    def fn(*, user_id: str) -> str:
        return "ok"

    for _ in range(3):
        assert fn(user_id="u1") == "ok"


def test_blocks_above_limit() -> None:
    @rate_limited(max_per_min=2)
    def fn(*, user_id: str) -> str:
        return "ok"

    fn(user_id="u1")
    fn(user_id="u1")
    with pytest.raises(RateLimitExceeded):
        fn(user_id="u1")


def test_per_user_isolation() -> None:
    @rate_limited(max_per_min=1)
    def fn(*, user_id: str) -> str:
        return "ok"

    fn(user_id="u1")
    # u2 ne doit pas être bloqué par u1.
    assert fn(user_id="u2") == "ok"


def test_window_slides() -> None:
    @rate_limited(max_per_min=1, window_seconds=0.01)
    def fn(*, user_id: str) -> str:
        return "ok"

    fn(user_id="u1")
    time.sleep(0.02)
    # Après la fenêtre glissante, le bucket est purgé.
    assert fn(user_id="u1") == "ok"


def test_anonymous_when_no_user_id() -> None:
    @rate_limited(max_per_min=1)
    def fn(**kwargs: object) -> str:
        return "ok"

    fn()
    with pytest.raises(RateLimitExceeded):
        fn()
