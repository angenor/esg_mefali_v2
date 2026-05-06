"""F58 / T036, T075 — select_tools filtre + mode minimal."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.agent.nodes.select_tools import (
    MINIMAL_MODE_TOOLS,
    SOURCING_FORCED_TOOLS,
    node_select_tools,
)
from app.agent.state import AgentState, ContextJson, Intent


def _make_state() -> AgentState:
    aid = uuid4()
    cid = uuid4()
    return AgentState(
        thread_id=f"{aid}:{cid}",
        account_id=aid,
        user_id=uuid4(),
        user_message="Hello",
        context_json=ContextJson(page_route="/"),
        intent=Intent.AUTRE,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_select_tools_excludes_disabled_tools() -> None:
    """Si un tool est désactivé, il ne doit pas apparaître dans available_tools."""
    state = _make_state()

    # Mock get_disabled_tools pour retourner un tool précis
    fake_disabled = {"create_project", "generate_dossier"}
    with patch(
        "app.agent.guardrails.tool_status.get_disabled_tools",
        return_value=fake_disabled,
    ):
        patch_state = await node_select_tools(state)

    available = patch_state.get("available_tools", [])
    for d in fake_disabled:
        assert d not in available, f"tool désactivé {d} encore présent: {available}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_select_tools_minimal_mode_restricts_to_sourcing_only() -> None:
    """En mode minimal, seuls cite_source + flag_unsourced sont autorisés."""
    state = _make_state()

    # Force LLM_AGENT_MODE = minimal pour ce test
    from app.config import get_settings

    settings = get_settings()
    original_mode = settings.LLM_AGENT_MODE
    settings.LLM_AGENT_MODE = "minimal"  # type: ignore[misc]
    try:
        patch_state = await node_select_tools(state)
    finally:
        settings.LLM_AGENT_MODE = original_mode  # type: ignore[misc]

    available = set(patch_state.get("available_tools", []))
    # Only minimal-allowed tools
    for tool in available:
        assert tool in MINIMAL_MODE_TOOLS, (
            f"tool {tool} interdit en mode minimal (autorisés : {MINIMAL_MODE_TOOLS})"
        )
    # Et les 2 sourcing tools sont bien présents
    assert MINIMAL_MODE_TOOLS.issubset(available)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_select_tools_normal_mode_includes_sourcing_tools() -> None:
    """En mode langgraph normal, sourcing tools sont forcés."""
    state = _make_state()
    with patch(
        "app.agent.guardrails.tool_status.get_disabled_tools",
        return_value=set(),
    ):
        patch_state = await node_select_tools(state)
    available = set(patch_state.get("available_tools", []))
    # Tous les sourcing tools forcés sont présents
    for forced in SOURCING_FORCED_TOOLS:
        assert forced in available, f"sourcing tool {forced} manquant: {available}"
