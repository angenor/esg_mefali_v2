"""Tests F16 — show_radar_chart."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.show_radar_chart import (
    ShowRadarChartPayload,
    register,
)


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Profil ESG",
        "axes": ["E", "S", "G", "Climat", "Div"],
        "series": [
            {"name": "Mefali", "values": ["72", "65", "80", "60", "75"]},
            {"name": "GCF", "values": ["75", "70", "78", "70", "72"]},
        ],
        "source_ids": [21, 22],
        "alt_text": "Radar 5 axes 2 séries.",
    }
    base.update(overrides)
    return base


def test_register_adds_tool() -> None:
    register()
    assert "show_radar_chart" in TOOL_REGISTRY


def test_basic_payload_ok() -> None:
    p = ShowRadarChartPayload(**_payload())
    assert len(p.axes) == 5
    assert len(p.series) == 2


def test_series_length_must_match_axes() -> None:
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(
            **_payload(series=[{"name": "Mefali", "values": ["1", "2", "3"]}])
        )


def test_too_few_axes_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(
            **_payload(
                axes=["E", "S"],
                series=[{"name": "Mefali", "values": ["1", "2"]}],
            )
        )


def test_too_many_axes_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(
            **_payload(
                axes=[f"a{i}" for i in range(13)],
                series=[{"name": "x", "values": [str(i) for i in range(13)]}],
            )
        )


def test_too_many_series_rejected() -> None:
    series = [
        {"name": f"s{i}", "values": ["1", "2", "3", "4", "5"]}
        for i in range(6)
    ]
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(**_payload(series=series))


def test_xss_in_title_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(**_payload(title="<x>"))


def test_xss_in_axis_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(**_payload(axes=["E", "<x>", "G", "C", "D"]))


def test_xss_in_series_name_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(
            **_payload(
                series=[{"name": "<bad>", "values": ["1", "2", "3", "4", "5"]}]
            )
        )


def test_source_ids_required() -> None:
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(**_payload(source_ids=[]))


def test_decimal_serialized_string() -> None:
    p = ShowRadarChartPayload(**_payload())
    dumped = p.model_dump(mode="json")
    assert isinstance(dumped["series"][0]["values"][0], str)


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowRadarChartPayload(**_payload(extra="x"))
