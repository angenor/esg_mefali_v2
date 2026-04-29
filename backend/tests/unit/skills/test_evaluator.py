"""F20 — Tests unit eval runner stub."""

from __future__ import annotations

import pytest

from app.skills.evaluator import run_eval


@pytest.mark.unit
def test_empty_examples_returns_zero_rates_and_blocks_gating() -> None:
    report = run_eval(["respond_user"], [])
    assert report.examples_count == 0
    assert report.tool_match_rate == 0.0
    assert report.payload_valid_rate == 0.0
    assert report.fallback_rate == 1.0
    assert report.gating_pass is False


@pytest.mark.unit
def test_perfect_match_passes_gating() -> None:
    examples = [
        {"expected_tool": "respond_user", "expected_payload": {"text": "ok"}}
        for _ in range(5)
    ]
    report = run_eval(["respond_user"], examples)
    assert report.tool_match_rate == 1.0
    assert report.payload_valid_rate == 1.0
    assert report.fallback_rate == 0.0
    assert report.gating_pass is True


@pytest.mark.unit
def test_partial_match_below_gating_threshold() -> None:
    examples = [
        {"expected_tool": "respond_user", "expected_payload": {"text": "ok"}},
        {"expected_tool": "unknown_tool", "expected_payload": {}},
        {"expected_tool": "unknown_tool", "expected_payload": None},
    ]
    report = run_eval(["respond_user"], examples)
    assert report.tool_match_rate == pytest.approx(1 / 3)
    assert report.payload_valid_rate == pytest.approx(1 / 3)
    assert report.gating_pass is False


@pytest.mark.unit
def test_unknown_tool_increments_fallback_rate() -> None:
    examples = [
        {"expected_tool": "x", "expected_payload": {}},
        {"expected_tool": "x", "expected_payload": {}},
    ]
    report = run_eval(["respond_user"], examples)
    assert report.fallback_rate == 1.0
    assert report.tool_match_rate == 0.0


@pytest.mark.unit
def test_empty_payload_dict_not_valid() -> None:
    examples = [{"expected_tool": "respond_user", "expected_payload": {}}]
    report = run_eval(["respond_user"], examples)
    assert report.tool_match_rate == 1.0
    assert report.payload_valid_rate == 0.0


@pytest.mark.unit
def test_non_dict_example_ignored_for_match() -> None:
    examples = [
        "not a dict",  # type: ignore[list-item]
        {"expected_tool": "respond_user", "expected_payload": {"k": 1}},
    ]
    report = run_eval(["respond_user"], examples)  # type: ignore[arg-type]
    assert report.examples_count == 2
    assert report.tool_match_rate == 0.5


@pytest.mark.unit
def test_as_dict_serialises_all_fields() -> None:
    examples = [{"expected_tool": "respond_user", "expected_payload": {"x": 1}}]
    report = run_eval(["respond_user"], examples)
    payload = report.as_dict()
    assert set(payload.keys()) == {
        "examples_count",
        "tool_match_rate",
        "payload_valid_rate",
        "fallback_rate",
        "gating_pass",
    }


@pytest.mark.unit
def test_gating_threshold_just_below_blocks() -> None:
    examples = [
        {"expected_tool": "respond_user", "expected_payload": {"k": 1}},
        {"expected_tool": "respond_user", "expected_payload": {"k": 1}},
        {"expected_tool": "respond_user", "expected_payload": {"k": 1}},
        {"expected_tool": "respond_user", "expected_payload": {"k": 1}},
        {"expected_tool": "missing", "expected_payload": {}},
    ]
    report = run_eval(["respond_user"], examples)
    assert report.tool_match_rate == 0.8
    assert report.payload_valid_rate == 0.8
    assert report.gating_pass is False
