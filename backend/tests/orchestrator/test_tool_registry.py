"""Tests du tool registry F14 (US4)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from app.orchestrator.fixtures_tools import register_fixture_tools
from app.orchestrator.tool_registry import (
    TOOL_REGISTRY,
    UnknownToolError,
    get_tool,
    tool,
)


class _StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class _LaxPayload(BaseModel):
    name: str


def test_tool_registers_in_global_registry() -> None:
    tool(
        name="t_demo",
        description="d",
        use_when="u",
        dont_use_when="dd",
        schema=_StrictPayload,
    )
    assert "t_demo" in TOOL_REGISTRY


def test_tool_duplicate_name_raises() -> None:
    tool(name="t_dup", description="d", use_when="u", dont_use_when="dd", schema=_StrictPayload)
    with pytest.raises(ValueError):
        tool(
            name="t_dup",
            description="d",
            use_when="u",
            dont_use_when="dd",
            schema=_StrictPayload,
        )


def test_tool_rejects_lax_schema() -> None:
    with pytest.raises(ValueError):
        tool(
            name="t_lax",
            description="d",
            use_when="u",
            dont_use_when="dd",
            schema=_LaxPayload,
        )


def test_get_tool_unknown_raises() -> None:
    with pytest.raises(UnknownToolError):
        get_tool("nope")


def test_fixture_tools_register_five() -> None:
    register_fixture_tools()
    expected = {
        "show_summary_card",
        "ask_qcu",
        "ask_yes_no",
        "update_demo_profile",
        "search_demo_source",
    }
    assert expected.issubset(TOOL_REGISTRY.keys())
    for name in expected:
        td = get_tool(name)
        assert td.schema.model_config.get("extra") == "forbid"
