"""F35 — Runner d'évaluation : exécute un golden set contre un callable LLM."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from app.eval.compare_payload import compare_payload
from app.eval.golden_loader import GoldenCase

FALLBACK_TOOL = "__fallback__"


@dataclass(frozen=True)
class LLMOutput:
    """Sortie minimale du LLM pour l'eval."""

    tool_name: str | None
    payload: dict[str, Any] | None = None
    error: str | None = None


@dataclass(frozen=True)
class CaseResult:
    """Résultat d'évaluation d'un cas."""

    id: str
    status: str
    reason: str | None
    expected_tool: str
    actual_tool: str | None
    duration_ms: int


@dataclass(frozen=True)
class EvalReport:
    """Rapport synthétique d'une exécution du runner."""

    total: int
    passed: int
    failed: int
    metrics: dict[str, float]
    cases: list[CaseResult] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _evaluate_case(case: GoldenCase, output: LLMOutput, duration_ms: int) -> CaseResult:
    """Évalue un seul cas. Pure function."""
    if output.error:
        return CaseResult(
            id=case.id,
            status="failed",
            reason=output.error,
            expected_tool=case.expected.tool,
            actual_tool=output.tool_name,
            duration_ms=duration_ms,
        )

    expected_tool = case.expected.tool
    actual_tool = output.tool_name

    if expected_tool == FALLBACK_TOOL:
        if actual_tool in (None, FALLBACK_TOOL):
            return CaseResult(
                id=case.id,
                status="passed",
                reason=None,
                expected_tool=expected_tool,
                actual_tool=actual_tool,
                duration_ms=duration_ms,
            )
        return CaseResult(
            id=case.id,
            status="failed",
            reason="expected_fallback_got_tool",
            expected_tool=expected_tool,
            actual_tool=actual_tool,
            duration_ms=duration_ms,
        )

    if actual_tool != expected_tool:
        return CaseResult(
            id=case.id,
            status="failed",
            reason="tool_mismatch",
            expected_tool=expected_tool,
            actual_tool=actual_tool,
            duration_ms=duration_ms,
        )

    match, reason = compare_payload(case.expected.payload_partial, output.payload)
    if not match:
        return CaseResult(
            id=case.id,
            status="failed",
            reason=f"payload_partial_mismatch:{reason}",
            expected_tool=expected_tool,
            actual_tool=actual_tool,
            duration_ms=duration_ms,
        )
    return CaseResult(
        id=case.id,
        status="passed",
        reason=None,
        expected_tool=expected_tool,
        actual_tool=actual_tool,
        duration_ms=duration_ms,
    )


def _compute_metrics(results: list[CaseResult]) -> dict[str, float]:
    """Calcule tool_match_rate / payload_partial_match_rate / fallback_rate."""
    total = len(results)
    if total == 0:
        return {
            "tool_match_rate": 0.0,
            "payload_partial_match_rate": 0.0,
            "fallback_rate": 0.0,
        }
    tool_ok = sum(
        1
        for r in results
        if r.actual_tool == r.expected_tool
        or (r.expected_tool == FALLBACK_TOOL and r.actual_tool in (None, FALLBACK_TOOL))
    )
    passed = sum(1 for r in results if r.status == "passed")
    fallbacks = sum(1 for r in results if r.actual_tool in (None, FALLBACK_TOOL))
    return {
        "tool_match_rate": round(tool_ok / total, 4),
        "payload_partial_match_rate": round(passed / total, 4),
        "fallback_rate": round(fallbacks / total, 4),
    }


def run_eval(
    cases: list[GoldenCase],
    llm_callable: Callable[[GoldenCase], LLMOutput],
) -> EvalReport:
    """Exécute le golden set et produit un rapport."""
    started = time.monotonic()
    results: list[CaseResult] = []
    for case in cases:
        case_start = time.monotonic()
        try:
            output = llm_callable(case)
        except Exception as exc:  # noqa: BLE001
            output = LLMOutput(tool_name=None, error=f"llm_exception:{type(exc).__name__}")
        duration_ms = int((time.monotonic() - case_start) * 1000)
        results.append(_evaluate_case(case, output, duration_ms))
    total = len(results)
    passed = sum(1 for r in results if r.status == "passed")
    failed = total - passed
    metrics = _compute_metrics(results)
    duration_ms = int((time.monotonic() - started) * 1000)
    return EvalReport(
        total=total,
        passed=passed,
        failed=failed,
        metrics=metrics,
        cases=results,
        duration_ms=duration_ms,
    )
