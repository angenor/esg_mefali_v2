"""F53 / T028 + T045 — Tests unitaires pour ``app/agent/nodes/dispatch_tool.py``."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from app.agent.nodes.dispatch_tool import (
    _clear_handlers_for_tests,
    needs_reinvoke,
    node_dispatch_tool,
    register_db_handler,
    register_reinvoke_handler,
)
from app.agent.state import (
    AgentState,
    ContextJson,
    DispatchCategory,
    ToolCall,
    ToolDispatchResult,
    ValidatedToolCall,
)
from app.orchestrator.tools import register_response_tools

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module", autouse=True)
def _setup_tools() -> None:
    try:
        register_response_tools()
    except ValueError:
        pass


@pytest.fixture(autouse=True)
def _clear_handlers():
    _clear_handlers_for_tests()
    yield
    _clear_handlers_for_tests()


def _state_with_validated(name: str, args: BaseModel | None = None) -> AgentState:
    if args is None:
        # Fake schema instance just for testing dispatch
        class _Fake(BaseModel):
            model_config = ConfigDict(extra="forbid")
            text: str = "x"

        args = _Fake()
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/"),
        tool_calls=[ToolCall(id="c1", name=name, arguments={"text": "x"})],
        validated_calls=[
            ValidatedToolCall(id="c1", name=name, arguments=args)
        ],
    )


@pytest.mark.asyncio
async def test_dispatch_sse_only_returns_ok() -> None:
    state = _state_with_validated("ask_qcu")
    state.account_id = uuid4()  # explicit
    patch = await node_dispatch_tool(state)
    assert "dispatch_results" in patch
    results = patch["dispatch_results"]
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, ToolDispatchResult)
    assert r.category == DispatchCategory.SSE_ONLY
    assert r.status == "ok"
    assert r.tool_call_id == "c1"


@pytest.mark.asyncio
async def test_dispatch_db_mutation_skipped_without_handler() -> None:
    """En F53 MVP, sans handler enregistré, on retourne ``skipped``."""
    state = _state_with_validated("create_projet")
    patch = await node_dispatch_tool(state)
    r = patch["dispatch_results"][0]
    assert r.category == DispatchCategory.DB_MUTATION
    assert r.status == "skipped"


@pytest.mark.asyncio
async def test_dispatch_db_mutation_with_handler_ok() -> None:
    async def handler(state, call):
        return {"id": "new-projet-id", "name": "fake"}

    register_db_handler("create_projet", handler)
    state = _state_with_validated("create_projet")
    patch = await node_dispatch_tool(state)
    r = patch["dispatch_results"][0]
    assert r.status == "ok"
    assert r.output == {"id": "new-projet-id", "name": "fake"}


@pytest.mark.asyncio
async def test_dispatch_db_mutation_handler_error_reported() -> None:
    async def handler(state, call):
        raise ValueError("constraint violation")

    register_db_handler("create_projet", handler)
    state = _state_with_validated("create_projet")
    patch = await node_dispatch_tool(state)
    r = patch["dispatch_results"][0]
    assert r.status == "error"
    assert "constraint" in (r.error_summary or "")
    # Et un AgentError "dispatch_error" est ajouté
    assert any(e.code == "dispatch_error" for e in patch.get("errors", []))


@pytest.mark.asyncio
async def test_dispatch_reinvoke_llm_increments_counter() -> None:
    state = _state_with_validated("recall_history")
    assert state.reinvoke_count == 0
    patch = await node_dispatch_tool(state)
    r = patch["dispatch_results"][0]
    assert r.category == DispatchCategory.REINVOKE_LLM
    assert r.status == "ok"
    assert patch.get("reinvoke_count") == 1
    # Un ToolMessage est injecté pour le LLM
    assert "messages" in patch and len(patch["messages"]) == 1


@pytest.mark.asyncio
async def test_dispatch_idempotent_on_already_dispatched() -> None:
    state = _state_with_validated("ask_qcu")
    state.dispatch_results.append(
        ToolDispatchResult(
            tool_call_id="c1",
            tool_name="ask_qcu",
            category=DispatchCategory.SSE_ONLY,
            status="ok",
        )
    )
    patch = await node_dispatch_tool(state)
    # Pas de re-dispatch
    assert patch == {} or "dispatch_results" not in patch


def test_needs_reinvoke_false_on_empty() -> None:
    state = AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/"),
    )
    assert needs_reinvoke(state) is False


def test_needs_reinvoke_true_with_reinvoke_dispatch() -> None:
    state = AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/"),
        dispatch_results=[
            ToolDispatchResult(
                tool_call_id="x",
                tool_name="recall_history",
                category=DispatchCategory.REINVOKE_LLM,
                status="ok",
            )
        ],
    )
    assert needs_reinvoke(state) is True


@pytest.mark.asyncio
async def test_dispatch_reinvoke_with_handler_passes_output() -> None:
    async def handler(state, call):
        return {"hits": [{"text": "older message", "id": "abc"}]}

    register_reinvoke_handler("recall_history", handler)
    state = _state_with_validated("recall_history")
    patch = await node_dispatch_tool(state)
    r = patch["dispatch_results"][0]
    assert r.status == "ok"
    assert r.output == {"hits": [{"text": "older message", "id": "abc"}]}
