"""Tests F16 — show_line_chart."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.show_line_chart import (
    ShowLineChartPayload,
    register,
)


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Empreinte 12 mois",
        "x_label": "Mois",
        "y_label": "tCO2e",
        "series": [
            {
                "name": "2025",
                "points": [
                    {"x": "2025-01", "y": "5.2"},
                    {"x": "2025-02", "y": "4.9"},
                ],
            }
        ],
        "source_ids": [42],
        "alt_text": "Line chart.",
    }
    base.update(overrides)
    return base


def test_register_adds_tool() -> None:
    register()
    assert "show_line_chart" in TOOL_REGISTRY


def test_basic_payload_ok() -> None:
    p = ShowLineChartPayload(**_payload())
    assert len(p.series) == 1
    assert len(p.series[0].points) == 2


def test_too_many_series_rejected() -> None:
    series = [
        {"name": f"s{i}", "points": [{"x": "a", "y": "1"}]} for i in range(6)
    ]
    with pytest.raises(ValidationError):
        ShowLineChartPayload(**_payload(series=series))


def test_too_many_points_rejected() -> None:
    points = [{"x": str(i), "y": str(i)} for i in range(51)]
    with pytest.raises(ValidationError):
        ShowLineChartPayload(
            **_payload(series=[{"name": "s", "points": points}])
        )


def test_empty_points_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowLineChartPayload(
            **_payload(series=[{"name": "s", "points": []}])
        )


def test_xss_in_title_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowLineChartPayload(**_payload(title="<x>"))


def test_xss_in_x_label_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowLineChartPayload(**_payload(x_label="<x>"))


def test_xss_in_series_name_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowLineChartPayload(
            **_payload(
                series=[{"name": "<bad>", "points": [{"x": "a", "y": "1"}]}]
            )
        )


def test_xss_in_point_x_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowLineChartPayload(
            **_payload(
                series=[{"name": "s", "points": [{"x": "<x>", "y": "1"}]}]
            )
        )


def test_source_ids_required() -> None:
    with pytest.raises(ValidationError):
        ShowLineChartPayload(**_payload(source_ids=[]))


def test_decimal_serialized_string() -> None:
    p = ShowLineChartPayload(**_payload())
    dumped = p.model_dump(mode="json")
    assert isinstance(dumped["series"][0]["points"][0]["y"], str)


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowLineChartPayload(**_payload(extra="x"))
