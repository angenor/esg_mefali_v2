"""Tests F15 — ask_number."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.ask_number import AskNumberPayload, register


def test_register_adds_tool() -> None:
    register()
    assert "ask_number" in TOOL_REGISTRY


def test_basic_payload() -> None:
    p = AskNumberPayload(question="Effectifs ?", unit="ETP", min=0, max=10000, step=1)
    assert p.unit == "ETP"
    assert p.money is None


def test_money_payload_xof() -> None:
    p = AskNumberPayload(question="CA ?", unit="XOF", min=0, money={"currency": "XOF"})
    assert p.money is not None
    assert p.money.currency == "XOF"


def test_money_invalid_currency_rejected() -> None:
    with pytest.raises(ValidationError):
        AskNumberPayload(question="CA ?", unit="USD", money={"currency": "USD"})


def test_min_greater_than_max_rejected() -> None:
    with pytest.raises(ValidationError):
        AskNumberPayload(question="X", unit="u", min=10, max=1)


def test_step_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        AskNumberPayload(question="X", unit="u", step=0)


def test_step_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        AskNumberPayload(question="X", unit="u", step=-1)


def test_html_in_question_rejected() -> None:
    with pytest.raises(ValidationError):
        AskNumberPayload(question="<x>", unit="u")


def test_html_in_unit_rejected() -> None:
    with pytest.raises(ValidationError):
        AskNumberPayload(question="ok ?", unit="<u>")


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        AskNumberPayload(question="ok ?", unit="u", rogue=1)
