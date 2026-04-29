"""F20 — Validation centralisée des payloads de skill."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.skills.activation_rules import parse_rules
from app.skills.anti_injection import scan as scan_injection
from app.skills.fusion import SKILL_PROMPT_MAX_TOKENS

SKILL_EVAL_GATING_TOOL_MATCH_MIN: float = 0.8
SKILL_EVAL_GATING_PAYLOAD_VALID_MIN: float = 0.9
SKILL_GOLDEN_EXAMPLES_MIN: int = 5


@dataclass
class ValidationReport:
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _known_tools() -> set[str]:
    try:
        from app.orchestrator.tool_registry import TOOL_REGISTRY

        if TOOL_REGISTRY:
            return set(TOOL_REGISTRY.keys())
    except Exception:  # noqa: BLE001
        pass
    return {
        "respond_user",
        "show_offre_details",
        "compare_offres",
        "match_offres",
        "pme_score",
        "start_diagnostic",
        "request_document",
        "simulate_amortization",
        "compute_carbon_footprint",
    }


def _check_required_fields(payload: dict[str, Any], report: ValidationReport) -> None:
    for fname in ("name", "domain", "prompt_expert"):
        val = payload.get(fname)
        if not isinstance(val, str) or not val.strip():
            report.errors.append(
                {"code": "missing_field", "field": fname, "message": f"Champ requis : {fname}"}
            )


def _check_prompt_size(payload: dict[str, Any], report: ValidationReport) -> None:
    prompt = payload.get("prompt_expert", "") or ""
    max_chars = SKILL_PROMPT_MAX_TOKENS * 4
    if len(prompt) > max_chars:
        report.errors.append(
            {
                "code": "prompt_too_long",
                "field": "prompt_expert",
                "message": f"Prompt trop long ({len(prompt)} > {max_chars} chars).",
                "limit_chars": max_chars,
            }
        )


def _check_anti_injection(
    payload: dict[str, Any], report: ValidationReport, *, override: bool
) -> None:
    issues = scan_injection(payload.get("prompt_expert", "") or "")
    if not issues:
        return
    serialised = [
        {"code": i.code, "message": i.message, "excerpt": i.excerpt} for i in issues
    ]
    if override:
        report.warnings.append(
            {
                "code": "prompt_injection_overridden",
                "message": "Patterns d'injection détectés — override admin.",
                "issues": serialised,
            }
        )
    else:
        report.errors.append(
            {
                "code": "prompt_injection_detected",
                "message": f"{len(issues)} pattern(s) suspect(s) détectés.",
                "issues": serialised,
            }
        )


def _check_activation_rules(payload: dict[str, Any], report: ValidationReport) -> None:
    rules = payload.get("activation_rules")
    if rules is None:
        return
    if not isinstance(rules, dict):
        report.errors.append(
            {
                "code": "activation_rules_invalid",
                "field": "activation_rules",
                "message": "activation_rules doit être un objet JSON.",
            }
        )
        return
    try:
        parse_rules(rules)
    except Exception as exc:  # noqa: BLE001
        report.errors.append(
            {
                "code": "activation_rules_invalid",
                "field": "activation_rules",
                "message": f"Schéma invalide : {exc}",
            }
        )


def _check_tool_whitelist(payload: dict[str, Any], report: ValidationReport) -> None:
    whitelist = payload.get("tool_whitelist") or []
    if not isinstance(whitelist, list):
        report.errors.append(
            {
                "code": "tool_whitelist_invalid",
                "field": "tool_whitelist",
                "message": "tool_whitelist doit être une liste de strings.",
            }
        )
        return
    known = _known_tools()
    unknown = [t for t in whitelist if t not in known]
    if unknown:
        report.errors.append(
            {
                "code": "tool_whitelist_unknown",
                "field": "tool_whitelist",
                "message": f"Tools inconnus : {unknown}",
                "unknown": unknown,
                "known_sample": sorted(known)[:20],
            }
        )


def _check_sources_verified(
    payload: dict[str, Any], db: Session, report: ValidationReport
) -> None:
    source_ids = payload.get("sources") or []
    if not source_ids:
        return
    if not isinstance(source_ids, list):
        report.errors.append(
            {
                "code": "sources_invalid",
                "field": "sources",
                "message": "sources doit être une liste d'UUIDs.",
            }
        )
        return
    rows = db.execute(
        text(
            "SELECT id, verification_status FROM source "
            "WHERE id = ANY(CAST(:ids AS UUID[]))"
        ),
        {"ids": [str(s) for s in source_ids]},
    ).all()
    found = {str(r._mapping["id"]): r._mapping["verification_status"] for r in rows}
    missing: list[dict[str, Any]] = []
    for sid in source_ids:
        sid_s = str(sid)
        if sid_s not in found:
            missing.append({"id": sid_s, "status": "unknown"})
        elif found[sid_s] != "verified":
            missing.append({"id": sid_s, "status": found[sid_s]})
    if missing:
        report.errors.append(
            {
                "code": "sources_not_verified",
                "field": "sources",
                "message": f"{len(missing)} source(s) non verified.",
                "missing": missing,
            }
        )


def _check_golden_examples(
    payload: dict[str, Any], report: ValidationReport, *, for_publish: bool
) -> None:
    examples = payload.get("golden_examples") or []
    if not isinstance(examples, list):
        report.errors.append(
            {
                "code": "golden_examples_invalid",
                "field": "golden_examples",
                "message": "golden_examples doit être une liste.",
            }
        )
        return
    if len(examples) < SKILL_GOLDEN_EXAMPLES_MIN:
        entry = {
            "code": "golden_examples_min",
            "field": "golden_examples",
            "message": (
                f"≥ {SKILL_GOLDEN_EXAMPLES_MIN} exemples recommandés "
                f"(actuel : {len(examples)})."
            ),
            "min": SKILL_GOLDEN_EXAMPLES_MIN,
            "actual": len(examples),
        }
        if for_publish:
            report.errors.append(entry)
        else:
            report.warnings.append(entry)


def validate_skill_payload(
    payload: dict[str, Any],
    db: Session,
    *,
    for_publish: bool = False,
    override_injection: bool = False,
) -> ValidationReport:
    """Valide un payload skill complet et retourne un ``ValidationReport``."""
    report = ValidationReport()
    _check_required_fields(payload, report)
    _check_prompt_size(payload, report)
    _check_anti_injection(payload, report, override=override_injection)
    _check_activation_rules(payload, report)
    _check_tool_whitelist(payload, report)
    _check_sources_verified(payload, db, report)
    _check_golden_examples(payload, report, for_publish=for_publish)
    return report


__all__ = [
    "SKILL_EVAL_GATING_PAYLOAD_VALID_MIN",
    "SKILL_EVAL_GATING_TOOL_MATCH_MIN",
    "SKILL_GOLDEN_EXAMPLES_MIN",
    "ValidationReport",
    "validate_skill_payload",
]
