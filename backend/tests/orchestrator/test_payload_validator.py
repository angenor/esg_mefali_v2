"""Tests du validateur Pydantic F14 (US6)."""

from __future__ import annotations

import pytest

from app.orchestrator.fixtures_tools import register_fixture_tools
from app.orchestrator.payload_validator import (
    UnknownToolError,
    format_for_llm,
    validate,
)
from app.orchestrator.tools import register_response_tools


def _register_all() -> None:
    register_fixture_tools()
    register_response_tools()


def test_validate_valid_payload_returns_ok() -> None:
    _register_all()
    ok, errors = validate("ask_yes_no", {"question": "Confirmer ?"})
    assert ok is True
    assert errors == []


def test_validate_extra_field_rejected() -> None:
    _register_all()
    ok, errors = validate(
        "ask_yes_no", {"question": "Confirmer ?", "rogue": "x"}
    )
    assert ok is False
    assert errors  # au moins une erreur


def test_validate_missing_field_rejected() -> None:
    _register_all()
    # ask_qcu requiert maintenant 'options' (>=2) — rejet attendu sans elles
    ok, errors = validate("ask_qcu", {"question": "X"})
    assert ok is False
    assert any("options" in e.field for e in errors)


def test_validate_wrong_type_rejected() -> None:
    _register_all()
    ok, errors = validate(
        "search_demo_source", {"query": "x", "top_k": "not-an-int"}
    )
    assert ok is False
    assert any("top_k" in e.field for e in errors)


def test_validate_enum_violation_rejected() -> None:
    _register_all()
    ok, errors = validate(
        "update_demo_profile", {"field": "unknown_field", "value": "v"}
    )
    assert ok is False


def test_validate_unknown_tool_raises() -> None:
    _register_all()
    with pytest.raises(UnknownToolError):
        validate("does_not_exist", {})


def test_format_for_llm_empty_returns_empty() -> None:
    assert format_for_llm([]) == ""


def test_format_for_llm_renders_lines() -> None:
    _register_all()
    _, errors = validate("ask_qcu", {"question": "X"})
    rendered = format_for_llm(errors)
    assert "Validation échouée" in rendered
    assert "options" in rendered
