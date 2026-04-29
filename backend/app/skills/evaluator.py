"""F20 — Eval runner stub MVP pour les ``golden_examples`` d'une skill."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.skills.validation import (
    SKILL_EVAL_GATING_PAYLOAD_VALID_MIN,
    SKILL_EVAL_GATING_TOOL_MATCH_MIN,
)


@dataclass(frozen=True)
class EvalReport:
    examples_count: int
    tool_match_rate: float
    payload_valid_rate: float
    fallback_rate: float
    gating_pass: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_eval(
    skill_tool_whitelist: list[str], golden_examples: list[dict[str, Any]]
) -> EvalReport:
    """Stub déterministe — rates calculés sans appel LLM."""
    n = len(golden_examples)
    if n == 0:
        return EvalReport(
            examples_count=0,
            tool_match_rate=0.0,
            payload_valid_rate=0.0,
            fallback_rate=1.0,
            gating_pass=False,
        )
    whitelist = set(skill_tool_whitelist or [])
    tool_matches = sum(
        1
        for ex in golden_examples
        if isinstance(ex, dict) and ex.get("expected_tool") in whitelist
    )
    payload_valid = sum(
        1
        for ex in golden_examples
        if isinstance(ex, dict)
        and isinstance(ex.get("expected_payload"), dict)
        and ex["expected_payload"]
    )
    tool_rate = tool_matches / n
    payload_rate = payload_valid / n
    return EvalReport(
        examples_count=n,
        tool_match_rate=tool_rate,
        payload_valid_rate=payload_rate,
        fallback_rate=1 - tool_rate,
        gating_pass=(
            tool_rate >= SKILL_EVAL_GATING_TOOL_MATCH_MIN
            and payload_rate >= SKILL_EVAL_GATING_PAYLOAD_VALID_MIN
        ),
    )


__all__ = ["EvalReport", "run_eval"]
