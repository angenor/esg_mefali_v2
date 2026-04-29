"""Tests F15 — ask_qcu."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.ask_qcu import AskQcuPayload, register


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "question": "Quelle forme juridique ?",
        "options": [
            {"value": "SARL", "label": "SARL"},
            {"value": "SA", "label": "SA"},
        ],
    }
    base.update(overrides)
    return base


def test_register_adds_tool_to_registry() -> None:
    register()
    assert "ask_qcu" in TOOL_REGISTRY
    assert TOOL_REGISTRY["ask_qcu"].schema is AskQcuPayload


def test_valid_payload_parses() -> None:
    p = AskQcuPayload(**_payload())
    assert p.allow_other is False
    assert len(p.options) == 2


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcuPayload(**_payload(rogue="x"))


def test_too_few_options_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcuPayload(**_payload(options=[{"value": "a", "label": "A"}]))


def test_too_many_options_rejected() -> None:
    options = [{"value": str(i), "label": f"o{i}"} for i in range(8)]
    with pytest.raises(ValidationError):
        AskQcuPayload(**_payload(options=options))


def test_html_in_question_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcuPayload(**_payload(question="<script>alert(1)</script>"))


def test_html_in_option_label_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcuPayload(
            **_payload(
                options=[
                    {"value": "x", "label": "<b>x</b>"},
                    {"value": "y", "label": "y"},
                ]
            )
        )


def test_html_in_option_description_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcuPayload(
            **_payload(
                options=[
                    {"value": "x", "label": "x", "description": "<i>desc</i>"},
                    {"value": "y", "label": "y"},
                ]
            )
        )
