"""Tests F15 — ask_yes_no."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.ask_yes_no import AskYesNoPayload, register


def test_register_adds_tool() -> None:
    register()
    assert "ask_yes_no" in TOOL_REGISTRY


def test_defaults_applied() -> None:
    p = AskYesNoPayload(question="Confirmer ?")
    assert p.yes_label == "Oui"
    assert p.no_label == "Non"


def test_custom_labels() -> None:
    p = AskYesNoPayload(question="Confirmer ?", yes_label="Confirmer", no_label="Annuler")
    assert p.yes_label == "Confirmer"
    assert p.no_label == "Annuler"


def test_html_in_question_rejected() -> None:
    with pytest.raises(ValidationError):
        AskYesNoPayload(question="<x>")


def test_html_in_yes_label_rejected() -> None:
    with pytest.raises(ValidationError):
        AskYesNoPayload(question="ok ?", yes_label="<b>oui</b>")


def test_html_in_no_label_rejected() -> None:
    with pytest.raises(ValidationError):
        AskYesNoPayload(question="ok ?", no_label="<i>non</i>")


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        AskYesNoPayload(question="ok ?", rogue=1)
