"""Tests F16 — register_visualisation_tools (intégration)."""

from __future__ import annotations

import pytest

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools import register_visualisation_tools

EXPECTED_P1_MVP_TOOLS = (
    "show_kpi_card",
    "show_radar_chart",
    "show_bar_chart",
    "show_line_chart",
)


def test_register_visualisation_tools_registers_all_p1_mvp() -> None:
    register_visualisation_tools()
    for name in EXPECTED_P1_MVP_TOOLS:
        assert name in TOOL_REGISTRY, f"{name} non enregistré"


def test_register_visualisation_tools_double_call_raises() -> None:
    register_visualisation_tools()
    n1 = len(TOOL_REGISTRY)
    with pytest.raises(ValueError):
        register_visualisation_tools()
    assert len(TOOL_REGISTRY) == n1


def test_each_visualisation_tool_has_strict_schema() -> None:
    register_visualisation_tools()
    for name in EXPECTED_P1_MVP_TOOLS:
        tool_def = TOOL_REGISTRY[name]
        assert tool_def.schema.model_config.get("extra") == "forbid"


def test_each_visualisation_tool_has_positive_example() -> None:
    register_visualisation_tools()
    for name in EXPECTED_P1_MVP_TOOLS:
        tool_def = TOOL_REGISTRY[name]
        assert len(tool_def.positive_examples) >= 1


def test_visualisation_and_response_tools_coexist() -> None:
    from app.orchestrator.tools import register_response_tools

    register_response_tools()
    register_visualisation_tools()
    assert "ask_qcu" in TOOL_REGISTRY
    assert "show_kpi_card" in TOOL_REGISTRY
