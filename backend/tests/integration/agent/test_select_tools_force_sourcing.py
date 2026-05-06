"""F56 / T011 — Test integration: ``select_tools`` force les 3 sourcing tools.

Vérifie :
1. Mode ``strict`` ⇒ les 3 tools sourcing sont injectés en plus des tools
   métier retournés par F14, même si le sélecteur retourne 10 tools.
2. Mode ``off`` ⇒ aucune injection forcée.
3. Si le sélecteur inclut déjà ``cite_source``, on ne le duplique pas.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.agent.nodes.select_tools import (
    SOURCING_FORCED_TOOLS,
    node_select_tools,
)
from app.agent.state import AgentState, ContextJson, Intent


def _build_state(*, intent: Intent = Intent.AUTRE) -> AgentState:
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hello",
        context_json=ContextJson(page_route="/chat"),
        intent=intent,
    )


@pytest.fixture(autouse=True)
def _ensure_sourcing_tools() -> None:
    import app.orchestrator.tools.sourcing  # noqa: F401


@pytest.mark.integration
async def test_strict_mode_injects_three_sourcing_tools_when_absent() -> None:
    state = _build_state()
    fake_business_tools = ["ask_qcu", "show_kpi_card", "create_project"]

    with (
        patch(
            "app.agent.nodes.select_tools.list_tool_names",
            return_value=fake_business_tools,
        ),
        patch(
            "app.agent.nodes.select_tools.get_settings"
        ) as p_settings,
    ):
        p_settings.return_value.LLM_AGENT_MAX_TOOLS = 10
        p_settings.return_value.LLM_AGENT_SOURCING_MODE = "strict"

        out = await node_select_tools(state)

    tools = out["available_tools"]
    for forced in SOURCING_FORCED_TOOLS:
        assert forced in tools, f"missing forced tool {forced} in {tools}"
    # 3 business + 3 forced = 6
    assert len(tools) == 6


@pytest.mark.integration
async def test_strict_mode_appends_sourcing_beyond_max_tools_cap() -> None:
    """Cap métier 10 atteint → 13 tools exposés (10 + 3 forcés)."""
    state = _build_state()
    fake_business_tools = [f"tool_{i}" for i in range(10)]

    with (
        patch(
            "app.agent.nodes.select_tools.list_tool_names",
            return_value=fake_business_tools,
        ),
        patch(
            "app.agent.nodes.select_tools.get_settings"
        ) as p_settings,
    ):
        p_settings.return_value.LLM_AGENT_MAX_TOOLS = 10
        p_settings.return_value.LLM_AGENT_SOURCING_MODE = "strict"
        out = await node_select_tools(state)

    tools = out["available_tools"]
    assert len(tools) == 13, f"expected 13 (10+3 forced), got {len(tools)}"


@pytest.mark.integration
async def test_off_mode_does_not_force_sourcing_tools() -> None:
    state = _build_state()
    fake_business_tools = ["ask_qcu", "show_kpi_card"]

    with (
        patch(
            "app.agent.nodes.select_tools.list_tool_names",
            return_value=fake_business_tools,
        ),
        patch(
            "app.agent.nodes.select_tools.get_settings"
        ) as p_settings,
    ):
        p_settings.return_value.LLM_AGENT_MAX_TOOLS = 10
        p_settings.return_value.LLM_AGENT_SOURCING_MODE = "off"
        out = await node_select_tools(state)

    tools = out["available_tools"]
    for forced in SOURCING_FORCED_TOOLS:
        assert forced not in tools, f"unexpected forced tool {forced}"
    assert tools == fake_business_tools


@pytest.mark.integration
async def test_does_not_duplicate_forced_tool_already_selected() -> None:
    state = _build_state()
    fake_business_tools = ["cite_source", "ask_qcu"]

    with (
        patch(
            "app.agent.nodes.select_tools.list_tool_names",
            return_value=fake_business_tools,
        ),
        patch(
            "app.agent.nodes.select_tools.get_settings"
        ) as p_settings,
    ):
        p_settings.return_value.LLM_AGENT_MAX_TOOLS = 10
        p_settings.return_value.LLM_AGENT_SOURCING_MODE = "strict"
        out = await node_select_tools(state)

    tools = out["available_tools"]
    # cite_source ne doit pas apparaître deux fois
    assert tools.count("cite_source") == 1
    # search_source et flag_unsourced doivent être ajoutés
    assert "search_source" in tools
    assert "flag_unsourced" in tools


@pytest.mark.integration
async def test_permissive_mode_also_forces_sourcing_tools() -> None:
    state = _build_state()
    fake_business_tools = ["ask_qcu"]

    with (
        patch(
            "app.agent.nodes.select_tools.list_tool_names",
            return_value=fake_business_tools,
        ),
        patch(
            "app.agent.nodes.select_tools.get_settings"
        ) as p_settings,
    ):
        p_settings.return_value.LLM_AGENT_MAX_TOOLS = 10
        p_settings.return_value.LLM_AGENT_SOURCING_MODE = "permissive"
        out = await node_select_tools(state)

    for forced in SOURCING_FORCED_TOOLS:
        assert forced in out["available_tools"]
