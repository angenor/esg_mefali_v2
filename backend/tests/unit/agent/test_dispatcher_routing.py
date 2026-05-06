"""F55 / T097 — Unit tests dispatcher routing.

Tests le routage par catégorie sans dépendance DB (les MUTATION sont testées
en intégration). On vérifie ASK/SHOW/READ comportements.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict, Field

from app.agent import dispatcher
from app.agent.state import (
    AgentState,
    ContextJson,
    ToolCategory,
    ValidatedToolCall,
)
from app.orchestrator.tool_registry import (
    TOOL_REGISTRY,
    reset_registry,
    tool,
)

pytestmark = pytest.mark.unit


class _AskArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1)


class _ShowArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str


@pytest.fixture(autouse=True)
def _registry_isolation():
    backup = dict(TOOL_REGISTRY)
    reset_registry()
    yield
    reset_registry()
    TOOL_REGISTRY.update(backup)


def _make_state(**kwargs):
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/chat"),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_ask_dispatch_returns_frontend_event():
    tool(
        name="ask_test_unit",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_AskArgs,
        category=ToolCategory.ASK,
    )
    call = ValidatedToolCall(
        id="c1",
        name="ask_test_unit",
        arguments=_AskArgs(question="Quoi?"),
    )
    state = _make_state()
    db = MagicMock()
    result = await dispatcher.dispatch(call, state, db)
    assert result.kind == "frontend_event"
    assert result.status == "ok"
    assert result.output["arguments"] == {"question": "Quoi?"}


@pytest.mark.asyncio
async def test_show_dispatch_returns_frontend_event():
    tool(
        name="show_test_unit",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_ShowArgs,
        category=ToolCategory.SHOW,
    )
    call = ValidatedToolCall(
        id="c2", name="show_test_unit", arguments=_ShowArgs(title="X")
    )
    state = _make_state()
    db = MagicMock()
    result = await dispatcher.dispatch(call, state, db)
    assert result.kind == "frontend_event"
    assert result.output["category"] == "show"


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    call = ValidatedToolCall(
        id="c3", name="not_in_registry", arguments=_AskArgs(question="x")
    )
    state = _make_state()
    db = MagicMock()
    result = await dispatcher.dispatch(call, state, db)
    assert result.kind == "error"
    assert result.error_summary == "tool_not_registered"


@pytest.mark.asyncio
async def test_hard_cap_reached_returns_error():
    tool(
        name="ask_x",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_AskArgs,
        category=ToolCategory.ASK,
    )
    call = ValidatedToolCall(
        id="c4", name="ask_x", arguments=_AskArgs(question="?")
    )
    state = _make_state(tool_calls_count_in_turn=10)
    db = MagicMock()
    result = await dispatcher.dispatch(call, state, db)
    assert result.kind == "error"
    assert result.error_summary == "tool_calls_cap_reached"


@pytest.mark.asyncio
async def test_hooks_before_after_called():
    dispatcher.reset_hooks()
    counter = {"before": 0, "after": 0}

    @dispatcher.before_dispatch
    async def _before(call, state):
        counter["before"] += 1

    @dispatcher.after_dispatch
    async def _after(call, result):
        counter["after"] += 1

    tool(
        name="ask_hook",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_AskArgs,
        category=ToolCategory.ASK,
    )
    call = ValidatedToolCall(
        id="c5", name="ask_hook", arguments=_AskArgs(question="?")
    )
    state = _make_state()
    db = MagicMock()
    await dispatcher.dispatch(call, state, db)
    assert counter["before"] == 1
    assert counter["after"] == 1
    dispatcher.reset_hooks()


@pytest.mark.asyncio
async def test_hooks_exceptions_absorbed():
    dispatcher.reset_hooks()

    @dispatcher.before_dispatch
    async def _bad_before(call, state):
        raise RuntimeError("boom")

    tool(
        name="ask_hook_err",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_AskArgs,
        category=ToolCategory.ASK,
    )
    call = ValidatedToolCall(
        id="c6", name="ask_hook_err", arguments=_AskArgs(question="?")
    )
    state = _make_state()
    db = MagicMock()
    # Ne doit PAS raise
    result = await dispatcher.dispatch(call, state, db)
    assert result.status == "ok"
    dispatcher.reset_hooks()


@pytest.mark.asyncio
async def test_read_tool_returns_tool_message():
    tool(
        name="recall_unit_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_AskArgs,
        category=ToolCategory.READ,
    )
    call = ValidatedToolCall(
        id="c7", name="recall_unit_test", arguments=_AskArgs(question="?")
    )
    state = _make_state()
    db = MagicMock()
    result = await dispatcher.dispatch(call, state, db)
    assert result.kind == "tool_message"
    assert "content" in (result.output or {})


@pytest.mark.asyncio
async def test_read_tool_with_handler():
    from app.agent.nodes.dispatch_tool import (
        _clear_handlers_for_tests,
        register_reinvoke_handler,
    )

    _clear_handlers_for_tests()
    tool(
        name="recall_with_handler",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_AskArgs,
        category=ToolCategory.READ,
    )

    async def _handler(state, call):
        return {"hits": [{"id": "1", "text": "hello"}]}

    register_reinvoke_handler("recall_with_handler", _handler)

    call = ValidatedToolCall(
        id="c8", name="recall_with_handler", arguments=_AskArgs(question="?")
    )
    state = _make_state()
    db = MagicMock()
    result = await dispatcher.dispatch(call, state, db)
    assert result.kind == "tool_message"
    content = result.output.get("content", "")
    assert "hello" in content
    _clear_handlers_for_tests()
