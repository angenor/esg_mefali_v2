"""F24 — Tests unitaires du rendu radar PNG."""

from __future__ import annotations

import pytest

from app.rapports.radar import (
    PNG_HEADER,
    _normalize_score,
    _ordered_axes,
    is_png,
    render_radar_png,
)


class TestNormalizeScore:
    def test_none_returns_zero(self) -> None:
        assert _normalize_score(None) == 0.0

    def test_clamp_below_zero(self) -> None:
        assert _normalize_score(-10) == 0.0

    def test_clamp_above_100(self) -> None:
        assert _normalize_score(150) == 100.0

    def test_passthrough(self) -> None:
        assert _normalize_score(42) == 42.0

    def test_invalid_string_returns_zero(self) -> None:
        assert _normalize_score("abc") == 0.0  # type: ignore[arg-type]


class TestOrderedAxes:
    def test_canonical_order(self) -> None:
        labels, values = _ordered_axes({"S": 80, "G": 70, "E": 60})
        assert labels == ["E", "S", "G"]
        assert values == [60.0, 80.0, 70.0]

    def test_extra_keys_appended_sorted(self) -> None:
        labels, _ = _ordered_axes({"E": 10, "Z": 1, "A": 2})
        assert labels[0] == "E"
        assert labels[-2:] == ["A", "Z"]

    def test_empty_returns_canonical(self) -> None:
        labels, values = _ordered_axes({})
        assert labels == ["E", "S", "G"]
        assert values == [0.0, 0.0, 0.0]


class TestRenderRadarPng:
    def test_returns_png_bytes(self) -> None:
        data = render_radar_png({"E": 70, "S": 80, "G": 60})
        assert isinstance(data, bytes)
        assert len(data) > 100
        assert data.startswith(PNG_HEADER)
        assert is_png(data)

    def test_handles_missing_pillars(self) -> None:
        data = render_radar_png({"E": 50})
        assert is_png(data)

    def test_empty_dict_still_renders(self) -> None:
        data = render_radar_png({})
        assert is_png(data)

    def test_custom_title(self) -> None:
        data = render_radar_png({"E": 1, "S": 2, "G": 3}, title="Custom")
        assert is_png(data)


@pytest.mark.parametrize(
    "scores",
    [
        {"E": 100, "S": 100, "G": 100},
        {"E": 0, "S": 0, "G": 0},
        {"E": None, "S": None, "G": None},
    ],
)
def test_render_extremes(scores: dict) -> None:
    assert is_png(render_radar_png(scores))
