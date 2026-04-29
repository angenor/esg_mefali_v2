"""Validateur Pydantic strict pour les payloads d'appels de tool (US6)."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.orchestrator.schemas import ValidationErrorDetail
from app.orchestrator.tool_registry import UnknownToolError, get_tool


def validate(tool_name: str, payload: dict[str, Any]) -> tuple[bool, list[ValidationErrorDetail]]:
    """Valide ``payload`` contre le schéma déclaré du tool.

    Retourne ``(True, [])`` si valide, sinon ``(False, errors)``.
    Lève ``UnknownToolError`` si le tool n'existe pas.
    """
    tool_def = get_tool(tool_name)
    try:
        tool_def.schema.model_validate(payload)
        return True, []
    except ValidationError as exc:
        errors = [_to_detail(err) for err in exc.errors()]
        return False, errors


def _to_detail(err: dict[str, Any]) -> ValidationErrorDetail:
    loc = err.get("loc", ())
    field = ".".join(str(p) for p in loc) if loc else "<root>"
    return ValidationErrorDetail(
        field=field,
        received=err.get("input"),
        expected=err.get("type", "unknown"),
        message=err.get("msg", "validation error"),
    )


def format_for_llm(errors: list[ValidationErrorDetail]) -> str:
    """Formate les erreurs en texte court à réinjecter dans le prompt retry."""
    if not errors:
        return ""
    lines = [f"- champ '{e.field}' : {e.message} (attendu : {e.expected})" for e in errors]
    return "Validation échouée :\n" + "\n".join(lines)


__all__ = ["validate", "format_for_llm", "UnknownToolError"]
