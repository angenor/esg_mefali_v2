"""Tests F16 — show_bar_chart."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.show_bar_chart import (
    ShowBarChartPayload,
    register,
)


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Score ESG par référentiel",
        "x_label": "Référentiel",
        "y_label": "Score",
        "bars": [
            {"label": "Mefali", "value": "72"},
            {"label": "GCF", "value": "68"},
        ],
        "source_ids": [21, 22],
        "alt_text": "Bar chart.",
    }
    base.update(overrides)
    return base


def test_register_adds_tool() -> None:
    register()
    assert "show_bar_chart" in TOOL_REGISTRY


def test_basic_payload_ok() -> None:
    p = ShowBarChartPayload(**_payload())
    assert len(p.bars) == 2


def test_too_many_bars_rejected() -> None:
    bars = [{"label": f"b{i}", "value": str(i)} for i in range(21)]
    with pytest.raises(ValidationError):
        ShowBarChartPayload(**_payload(bars=bars))


def test_empty_bars_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowBarChartPayload(**_payload(bars=[]))


def test_xss_in_title_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowBarChartPayload(**_payload(title="<x>"))


def test_xss_in_x_label_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowBarChartPayload(**_payload(x_label="<x>"))


def test_xss_in_bar_label_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowBarChartPayload(
            **_payload(bars=[{"label": "<x>", "value": "1"}])
        )


def test_source_ids_required() -> None:
    with pytest.raises(ValidationError):
        ShowBarChartPayload(**_payload(source_ids=[]))


def test_decimal_serialized_string() -> None:
    p = ShowBarChartPayload(**_payload())
    dumped = p.model_dump(mode="json")
    assert isinstance(dumped["bars"][0]["value"], str)


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowBarChartPayload(**_payload(extra="x"))
