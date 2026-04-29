"""Tests F15 — register_response_tools (intégration)."""

from __future__ import annotations

import pytest

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools import register_response_tools

EXPECTED_P1_TOOLS = (
    "ask_qcu",
    "ask_qcm",
    "ask_yes_no",
    "ask_select",
    "ask_number",
    "ask_file_upload",
    "show_summary_card",
)


def test_register_response_tools_registers_all_p1() -> None:
    register_response_tools()
    for name in EXPECTED_P1_TOOLS:
        assert name in TOOL_REGISTRY, f"{name} non enregistré"


def test_register_response_tools_double_call_raises() -> None:
    """Le registre F14 est immuable ; un doublon doit lever ValueError."""
    register_response_tools()
    n1 = len(TOOL_REGISTRY)
    with pytest.raises(ValueError):
        register_response_tools()
    assert len(TOOL_REGISTRY) == n1


def test_each_tool_has_strict_schema() -> None:
    register_response_tools()
    for name in EXPECTED_P1_TOOLS:
        tool_def = TOOL_REGISTRY[name]
        assert tool_def.schema.model_config.get("extra") == "forbid"
