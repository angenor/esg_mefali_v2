"""Tests du sélecteur de tools F14 (US3)."""

from __future__ import annotations

from app.orchestrator.fixtures_tools import register_fixture_tools
from app.orchestrator.tool_selector import DEFAULT_TOOLS, MAX_TOOLS, select
from app.orchestrator.tools import register_response_tools


def _register_all() -> None:
    register_fixture_tools()
    register_response_tools()


def test_select_mutation_returns_mutation_tools() -> None:
    _register_all()
    tools = select("mutation")
    assert "update_demo_profile" in tools
    assert len(tools) <= MAX_TOOLS


def test_select_aide_returns_default_set() -> None:
    _register_all()
    tools = select("aide")
    assert set(tools).issubset({"ask_qcu", "ask_yes_no"})
    assert tools


def test_select_never_exceeds_max() -> None:
    _register_all()
    for intent in (
        "mutation",
        "analyse",
        "aide",
        "question_fermee",
        "navigation",
        "profilage",
        "autre",
    ):
        assert len(select(intent)) <= MAX_TOOLS


def test_select_with_skill_whitelist_filters() -> None:
    _register_all()
    tools = select("mutation", skill_whitelist=("ask_qcu",))
    assert tools == ["ask_qcu"]


def test_select_empty_whitelist_falls_back_to_default() -> None:
    _register_all()
    tools = select("mutation", skill_whitelist=("nonexistent_tool",))
    assert all(t in DEFAULT_TOOLS for t in tools)
    assert tools


def test_select_never_returns_empty_when_registry_populated() -> None:
    _register_all()
    tools = select("autre")
    assert tools
