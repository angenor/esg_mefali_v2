"""Tests de la politique de retry F14 (US7)."""

from __future__ import annotations

from app.orchestrator.retry_policy import (
    FALLBACK_TEXT,
    MAX_RETRIES,
    build_retry_prompt,
    decide,
)
from app.orchestrator.schemas import ValidationErrorDetail


def test_decide_first_failure_retries() -> None:
    assert decide(retry_count=0) == "retry"


def test_decide_second_failure_retries() -> None:
    assert decide(retry_count=1) == "retry"


def test_decide_after_max_retries_fallback() -> None:
    assert decide(retry_count=MAX_RETRIES) == "fallback"
    assert decide(retry_count=MAX_RETRIES + 5) == "fallback"


def test_max_retries_is_two() -> None:
    assert MAX_RETRIES == 2


def test_fallback_text_non_empty() -> None:
    assert isinstance(FALLBACK_TEXT, str)
    assert len(FALLBACK_TEXT) > 0


def test_build_retry_prompt_includes_attempt_and_errors() -> None:
    err = ValidationErrorDetail(
        field="x", received=None, expected="str", message="missing"
    )
    prompt = build_retry_prompt([err], retry_count=0)
    assert "Tentative 1/" in prompt
    assert "x" in prompt
    assert "JSON" in prompt
