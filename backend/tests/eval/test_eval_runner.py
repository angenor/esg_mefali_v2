"""F35 — Tests pour ``eval_runner.run_eval``."""

from __future__ import annotations

import pytest

from app.eval.eval_runner import FALLBACK_TOOL, LLMOutput, run_eval
from app.eval.golden_loader import GoldenCase, GoldenContext, GoldenExpected


def _case(
    id: str,
    expected_tool: str,
    payload_partial: dict | None = None,
    tags: tuple[str, ...] = (),
) -> GoldenCase:
    return GoldenCase(
        id=id,
        description="t",
        context=GoldenContext(),
        user_message="m",
        expected=GoldenExpected(tool=expected_tool, payload_partial=payload_partial or {}),
        tags=tags,
    )


@pytest.mark.unit
def test_passed_when_tool_and_payload_match() -> None:
    case = _case(
        "c1", "ask_qcu", {"options_count_min": 2, "options_contain": ["SARL"]}
    )

    def fake_llm(_c: GoldenCase) -> LLMOutput:
        return LLMOutput(
            tool_name="ask_qcu",
            payload={"options": [{"label": "SARL"}, {"label": "SA"}]},
        )

    report = run_eval([case], fake_llm)
    assert report.total == 1
    assert report.passed == 1
    assert report.failed == 0
    assert report.cases[0].status == "passed"
    assert report.metrics["tool_match_rate"] == 1.0
    assert report.metrics["payload_partial_match_rate"] == 1.0


@pytest.mark.unit
def test_failed_on_tool_mismatch() -> None:
    case = _case("c1", "ask_qcu")

    def fake_llm(_c: GoldenCase) -> LLMOutput:
        return LLMOutput(tool_name="ask_qcm", payload={})

    report = run_eval([case], fake_llm)
    assert report.failed == 1
    assert report.cases[0].reason == "tool_mismatch"
    assert report.metrics["tool_match_rate"] == 0.0


@pytest.mark.unit
def test_failed_on_payload_partial_mismatch() -> None:
    case = _case("c1", "ask_qcu", {"options_count_min": 4})

    def fake_llm(_c: GoldenCase) -> LLMOutput:
        return LLMOutput(tool_name="ask_qcu", payload={"options": [{"label": "A"}]})

    report = run_eval([case], fake_llm)
    assert report.failed == 1
    assert report.cases[0].reason is not None
    assert report.cases[0].reason.startswith("payload_partial_mismatch:")
    assert report.metrics["tool_match_rate"] == 1.0
    assert report.metrics["payload_partial_match_rate"] == 0.0


@pytest.mark.unit
def test_fallback_passed_when_actual_none() -> None:
    case = _case("c1", FALLBACK_TOOL)

    def fake_llm(_c: GoldenCase) -> LLMOutput:
        return LLMOutput(tool_name=None, payload=None)

    report = run_eval([case], fake_llm)
    assert report.passed == 1
    assert report.metrics["fallback_rate"] == 1.0


@pytest.mark.unit
def test_fallback_failed_when_tool_returned() -> None:
    case = _case("c1", FALLBACK_TOOL)

    def fake_llm(_c: GoldenCase) -> LLMOutput:
        return LLMOutput(tool_name="ask_qcu", payload={})

    report = run_eval([case], fake_llm)
    assert report.failed == 1
    assert report.cases[0].reason == "expected_fallback_got_tool"


@pytest.mark.unit
def test_llm_exception_handled() -> None:
    case = _case("c1", "ask_qcu")

    def fake_llm(_c: GoldenCase) -> LLMOutput:
        raise RuntimeError("boom")

    report = run_eval([case], fake_llm)
    assert report.failed == 1
    assert report.cases[0].reason is not None
    assert report.cases[0].reason.startswith("llm_exception:")


@pytest.mark.unit
def test_llm_error_field_marks_failed() -> None:
    case = _case("c1", "ask_qcu")

    def fake_llm(_c: GoldenCase) -> LLMOutput:
        return LLMOutput(tool_name=None, error="llm_timeout")

    report = run_eval([case], fake_llm)
    assert report.failed == 1
    assert report.cases[0].reason == "llm_timeout"


@pytest.mark.unit
def test_empty_cases_returns_zero_metrics() -> None:
    report = run_eval([], lambda _c: LLMOutput(tool_name=None))
    assert report.total == 0
    assert report.metrics["tool_match_rate"] == 0.0


@pytest.mark.unit
def test_mixed_results_metrics() -> None:
    cases = [
        _case("ok", "ask_qcu"),
        _case("ko", "ask_qcm"),
        _case("fb", FALLBACK_TOOL),
    ]

    def fake_llm(c: GoldenCase) -> LLMOutput:
        if c.id == "ok":
            return LLMOutput(tool_name="ask_qcu", payload={})
        if c.id == "ko":
            return LLMOutput(tool_name="ask_qcu", payload={})
        return LLMOutput(tool_name=None, payload=None)

    report = run_eval(cases, fake_llm)
    assert report.passed == 2
    assert report.failed == 1
    assert report.metrics["tool_match_rate"] == round(2 / 3, 4)
    assert report.metrics["fallback_rate"] == round(1 / 3, 4)
