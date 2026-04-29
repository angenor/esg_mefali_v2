"""Tests F15 — ask_qcm."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.ask_qcm import AskQcmPayload, register


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "question": "Piliers ESG ?",
        "options": [
            {"value": "E", "label": "Environnement"},
            {"value": "S", "label": "Social"},
            {"value": "G", "label": "Gouvernance"},
        ],
    }
    base.update(overrides)
    return base


def test_register_adds_tool() -> None:
    register()
    assert "ask_qcm" in TOOL_REGISTRY


def test_valid_payload_parses() -> None:
    p = AskQcmPayload(**_payload(min_select=1, max_select=2))
    assert p.min_select == 1
    assert p.max_select == 2


def test_min_greater_than_max_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcmPayload(**_payload(min_select=3, max_select=1))


def test_min_greater_than_options_count_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcmPayload(**_payload(min_select=10))


def test_max_greater_than_options_count_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcmPayload(**_payload(max_select=10))


def test_too_few_options_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcmPayload(**_payload(options=[{"value": "x", "label": "X"}]))


def test_html_in_label_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcmPayload(
            **_payload(
                options=[
                    {"value": "x", "label": "<b>X</b>"},
                    {"value": "y", "label": "Y"},
                ]
            )
        )


def test_html_in_description_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcmPayload(
            **_payload(
                options=[
                    {"value": "x", "label": "X", "description": "<i>x</i>"},
                    {"value": "y", "label": "Y"},
                ]
            )
        )


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        AskQcmPayload(**_payload(rogue=1))
