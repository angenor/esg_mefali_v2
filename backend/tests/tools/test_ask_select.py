"""Tests F15 — ask_select."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.ask_select import AskSelectPayload, register


def test_register_adds_tool() -> None:
    register()
    assert "ask_select" in TOOL_REGISTRY


def test_options_inline_valid() -> None:
    p = AskSelectPayload(
        question="Pays ?",
        options=[
            {"value": "ci", "label": "Côte d'Ivoire"},
            {"value": "sn", "label": "Sénégal"},
        ],
    )
    assert p.multi is False
    assert p.options is not None


def test_options_endpoint_valid() -> None:
    p = AskSelectPayload(question="Secteur ?", options_endpoint="/me/catalog/secteurs")
    assert p.options_endpoint == "/me/catalog/secteurs"


def test_both_options_and_endpoint_rejected() -> None:
    with pytest.raises(ValidationError):
        AskSelectPayload(
            question="X ?",
            options=[{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
            options_endpoint="/x",
        )


def test_neither_options_nor_endpoint_rejected() -> None:
    with pytest.raises(ValidationError):
        AskSelectPayload(question="X ?")


def test_endpoint_must_start_with_slash() -> None:
    with pytest.raises(ValidationError):
        AskSelectPayload(question="X ?", options_endpoint="me/catalog/x")


def test_html_in_question_rejected() -> None:
    with pytest.raises(ValidationError):
        AskSelectPayload(question="<x>", options_endpoint="/x")


def test_html_in_inline_label_rejected() -> None:
    with pytest.raises(ValidationError):
        AskSelectPayload(
            question="X ?",
            options=[
                {"value": "a", "label": "<b>A</b>"},
                {"value": "b", "label": "B"},
            ],
        )


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        AskSelectPayload(question="X ?", options_endpoint="/x", rogue=1)
