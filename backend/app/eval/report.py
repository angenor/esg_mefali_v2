"""F35 — Sérialisation d'un ``EvalReport`` en JSON et Markdown."""

from __future__ import annotations

import json

from app.eval.eval_runner import EvalReport


def to_json(report: EvalReport, *, indent: int | None = 2) -> str:
    """Sérialise un rapport en JSON déterministe."""
    return json.dumps(report.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)


def to_markdown(report: EvalReport) -> str:
    """Sérialise un rapport en Markdown lisible."""
    lines: list[str] = []
    lines.append("# LLM Eval Report")
    lines.append("")
    lines.append(f"- **Total**: {report.total}")
    lines.append(f"- **Passed**: {report.passed}")
    lines.append(f"- **Failed**: {report.failed}")
    lines.append(f"- **Duration**: {report.duration_ms} ms")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    for k, v in sorted(report.metrics.items()):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    lines.append("| id | status | expected_tool | actual_tool | reason |")
    lines.append("|----|--------|---------------|-------------|--------|")
    for c in report.cases:
        reason = c.reason or ""
        lines.append(
            f"| {c.id} | {c.status} | {c.expected_tool} | {c.actual_tool or ''} | {reason} |"
        )
    return "\n".join(lines) + "\n"
