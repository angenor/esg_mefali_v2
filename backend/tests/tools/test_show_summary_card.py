"""Tests F15 — show_summary_card."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.show_summary_card import (
    ShowSummaryCardPayload,
    register,
)


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Récap",
        "fields": [
            {"label": "Nom", "value": "ACME"},
            {"label": "Effectifs", "value": "12"},
        ],
        "actions": [
            {"label": "Valider", "kind": "confirm"},
            {"label": "Annuler", "kind": "cancel"},
        ],
    }
    base.update(overrides)
    return base


def test_register_adds_tool() -> None:
    register()
    assert "show_summary_card" in TOOL_REGISTRY


def test_basic_payload() -> None:
    p = ShowSummaryCardPayload(**_payload())
    assert len(p.fields) == 2
    assert p.actions[0].kind == "confirm"


def test_invalid_action_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowSummaryCardPayload(
            **_payload(actions=[{"label": "Go", "kind": "submit"}])
        )


def test_empty_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowSummaryCardPayload(**_payload(fields=[]))


def test_empty_actions_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowSummaryCardPayload(**_payload(actions=[]))


def test_html_in_title_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowSummaryCardPayload(**_payload(title="<x>"))


def test_html_in_field_value_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowSummaryCardPayload(
            **_payload(
                fields=[
                    {"label": "Nom", "value": "<b>ACME</b>"},
                    {"label": "X", "value": "y"},
                ]
            )
        )


def test_html_in_field_source_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowSummaryCardPayload(
            **_payload(
                fields=[
                    {"label": "Nom", "value": "ACME", "source": "<a>x</a>"},
                    {"label": "X", "value": "y"},
                ]
            )
        )


def test_html_in_action_label_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowSummaryCardPayload(
            **_payload(actions=[{"label": "<b>OK</b>", "kind": "confirm"}])
        )


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowSummaryCardPayload(**_payload(rogue=1))
