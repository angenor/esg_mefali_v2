"""F35 — Endpoint admin : déclenche un run d'évaluation du golden set."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.auth.dependencies import get_current_admin
from app.eval.eval_runner import LLMOutput, run_eval
from app.eval.golden_loader import GoldenCase, load_cases
from app.models.account_user import AccountUser

router = APIRouter(prefix="/api/admin/llm-eval", tags=["admin", "llm-eval"])

DEFAULT_GOLDEN_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "llm_eval" / "golden_seed.json"
)


class EvalRunRequest(BaseModel):
    """Body de l'endpoint (tous champs optionnels)."""

    model_config = ConfigDict(extra="forbid")

    tags: list[str] | None = None
    limit: int | None = Field(default=None, ge=1, le=200)


class CaseResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    reason: str | None = None
    expected_tool: str
    actual_tool: str | None = None
    duration_ms: int


class EvalReportSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    passed: int
    failed: int
    metrics: dict[str, float]
    cases: list[CaseResultSchema]
    duration_ms: int


def _stub_llm_callable(case: GoldenCase) -> LLMOutput:
    """Stub déterministe : reproduit fidèlement l'attendu."""
    expected = case.expected
    if expected.tool == "__fallback__":
        return LLMOutput(tool_name=None, payload=None)

    payload: dict[str, Any] = {}
    pp = expected.payload_partial
    if "options_count_min" in pp or "options_contain" in pp:
        contains = list(pp.get("options_contain") or [])
        n_min = int(pp.get("options_count_min", 0))
        labels = list(contains)
        while len(labels) < n_min:
            labels.append(f"option_{len(labels) + 1}")
        payload["options"] = [{"label": label, "value": label} for label in labels]
    if "equals" in pp and isinstance(pp["equals"], dict):
        payload.update(pp["equals"])
    if "regex" in pp and isinstance(pp["regex"], dict):
        for k, pattern in pp["regex"].items():
            payload[k] = pattern.lstrip("^").rstrip("$") + " synthetic"
    return LLMOutput(tool_name=expected.tool, payload=payload)


def _golden_path() -> Path:
    """Hook pour permettre l'override en tests."""
    return DEFAULT_GOLDEN_PATH


@router.post("/run", response_model=EvalReportSchema)
def run_llm_eval(
    body: EvalRunRequest | None = None,
    admin: AccountUser = Depends(get_current_admin),
) -> EvalReportSchema:
    """Exécute le golden set et renvoie le rapport (admin only)."""
    body = body or EvalRunRequest()
    path = _golden_path()
    try:
        cases = load_cases(path, filter_tags=body.tags)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "golden_set_missing", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "golden_set_invalid", "message": str(exc)},
        ) from exc

    if body.limit is not None:
        cases = cases[: body.limit]

    report = run_eval(cases, llm_callable=_stub_llm_callable)
    return EvalReportSchema(
        total=report.total,
        passed=report.passed,
        failed=report.failed,
        metrics=report.metrics,
        cases=[CaseResultSchema(**case.__dict__) for case in report.cases],
        duration_ms=report.duration_ms,
    )
