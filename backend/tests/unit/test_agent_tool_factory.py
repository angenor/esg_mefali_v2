"""F53 / T016 — Tests unitaires pour ``app/agent/tool_factory.py``."""

from __future__ import annotations

import pytest
from langchain_core.tools import StructuredTool

from app.agent.state import DispatchCategory
from app.agent.tool_factory import (
    categorize,
    list_active_tools,
    list_tool_names,
    to_structured_tool,
)
from app.orchestrator.tool_registry import get_tool
from app.orchestrator.tools import register_response_tools

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module", autouse=True)
def _ensure_tools_registered() -> None:
    """Register response tools (idempotent : ignore les ré-enregistrements)."""
    try:
        register_response_tools()
    except ValueError:
        pass  # Already registered
    yield


class TestToStructuredTool:
    def test_returns_structured_tool(self) -> None:
        tool_def = get_tool("ask_qcu")
        st = to_structured_tool(tool_def)
        assert isinstance(st, StructuredTool)
        assert st.name == "ask_qcu"

    def test_description_includes_use_when(self) -> None:
        tool_def = get_tool("ask_qcu")
        st = to_structured_tool(tool_def)
        assert "Use when" in st.description
        assert "Don't use when" in st.description

    def test_args_schema_is_pydantic_extra_forbid(self) -> None:
        tool_def = get_tool("ask_qcu")
        st = to_structured_tool(tool_def)
        assert st.args_schema is tool_def.schema


class TestCategorize:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("ask_qcu", DispatchCategory.SSE_ONLY),
            ("ask_yes_no", DispatchCategory.SSE_ONLY),
            ("show_radar_chart", DispatchCategory.SSE_ONLY),
            ("show_summary_card", DispatchCategory.SSE_ONLY),
            ("update_demo_profile", DispatchCategory.DB_MUTATION),
            ("create_projet", DispatchCategory.DB_MUTATION),
            ("delete_projet", DispatchCategory.DB_MUTATION),
            ("cite_source", DispatchCategory.REINVOKE_LLM),
            ("search_source", DispatchCategory.REINVOKE_LLM),
            ("recall_history", DispatchCategory.REINVOKE_LLM),
        ],
    )
    def test_known_tools(self, name: str, expected: DispatchCategory) -> None:
        assert categorize(name) == expected

    def test_unknown_tool_defaults_sse(self) -> None:
        assert categorize("frobnicate") == DispatchCategory.SSE_ONLY


class TestListActiveTools:
    def test_returns_structured_tools_for_mutation(self) -> None:
        tools = list_active_tools("mutation")
        names = [t.name for t in tools]
        assert "ask_qcu" in names or "update_demo_profile" in names

    def test_max_tools_capped(self) -> None:
        tools = list_active_tools("mutation", max_tools=1)
        assert len(tools) <= 1

    def test_unknown_intent_falls_back_default(self) -> None:
        tools = list_active_tools("autre")
        # Doit toujours retourner quelque chose (default tools)
        assert len(tools) >= 1

    def test_returns_list_of_structured_tools(self) -> None:
        tools = list_active_tools("aide")
        for t in tools:
            assert isinstance(t, StructuredTool)


class TestListToolNames:
    def test_returns_strings(self) -> None:
        names = list_tool_names("mutation")
        assert all(isinstance(n, str) for n in names)

    def test_max_tools_cap(self) -> None:
        names = list_tool_names("mutation", max_tools=2)
        assert len(names) <= 2
