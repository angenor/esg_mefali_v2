"""F35 — Tests pour la sérialisation du rapport (JSON + Markdown)."""

from __future__ import annotations

import json

import pytest

from app.eval.eval_runner import CaseResult, EvalReport
from app.eval.report import to_json, to_markdown


def _sample_report() -> EvalReport:
    return EvalReport(
        total=2,
        passed=1,
        failed=1,
        metrics={
            "tool_match_rate": 0.5,
            "payload_partial_match_rate": 0.5,
            "fallback_rate": 0.0,
        },
        cases=[
            CaseResult(
                id="c1",
                status="passed",
                reason=None,
                expected_tool="ask_qcu",
                actual_tool="ask_qcu",
                duration_ms=10,
            ),
            CaseResult(
                id="c2",
                status="failed",
                reason="tool_mismatch",
                expected_tool="ask_qcu",
                actual_tool="ask_qcm",
                duration_ms=12,
            ),
        ],
        duration_ms=22,
    )


@pytest.mark.unit
def test_to_json_returns_valid_json() -> None:
    report = _sample_report()
    s = to_json(report)
    parsed = json.loads(s)
    assert parsed["total"] == 2
    assert parsed["passed"] == 1
    assert parsed["failed"] == 1
    assert parsed["metrics"]["tool_match_rate"] == 0.5
    assert isinstance(parsed["cases"], list)
    assert parsed["cases"][1]["reason"] == "tool_mismatch"


@pytest.mark.unit
def test_to_json_is_sorted_deterministic() -> None:
    report = _sample_report()
    a = to_json(report)
    b = to_json(report)
    assert a == b


@pytest.mark.unit
def test_to_markdown_contains_headers_and_table() -> None:
    md = to_markdown(_sample_report())
    assert "# LLM Eval Report" in md
    assert "## Metrics" in md
    assert "## Cases" in md
    assert "| id | status |" in md
    assert "| c1 | passed |" in md
    assert "tool_mismatch" in md


@pytest.mark.unit
def test_to_json_compact_no_indent() -> None:
    s = to_json(_sample_report(), indent=None)
    parsed = json.loads(s)
    assert parsed["total"] == 2
