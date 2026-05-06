"""F53 / T051 — Tests unitaires pour ``app/agent/nodes/validate_payload.py``."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from langchain_core.messages import ToolMessage

from app.agent.nodes.validate_payload import (
    has_pending_validation_failure,
    has_unvalidated_calls,
    node_validate_payload,
)
from app.agent.state import AgentState, ContextJson, ToolCall
from app.orchestrator.tools import register_response_tools

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module", autouse=True)
def _setup_tools() -> None:
    try:
        register_response_tools()
    except ValueError:
        pass


def _state_with_call(name: str, args: dict) -> AgentState:
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/"),
        tool_calls=[ToolCall(id="c1", name=name, arguments=args)],
    )


@pytest.mark.asyncio
async def test_validate_valid_payload_creates_validated_call() -> None:
    state = _state_with_call(
        "ask_qcu",
        {
            "question": "Quelle option ?",
            "options": [
                {"value": "a", "label": "A"},
                {"value": "b", "label": "B"},
            ],
        },
    )
    patch = await node_validate_payload(state)
    assert "validated_calls" in patch
    assert len(patch["validated_calls"]) == 1
    v = patch["validated_calls"][0]
    assert v.id == "c1"
    assert v.name == "ask_qcu"
    # ``retry_count`` ne doit PAS bouger sur succès
    assert "retry_count" not in patch


@pytest.mark.asyncio
async def test_validate_invalid_payload_emits_tool_message_and_increments_retry() -> None:
    state = _state_with_call(
        "ask_qcu",
        {
            "question": "Q",
            "options": [],  # min_length=2 → erreur
        },
    )
    patch = await node_validate_payload(state)
    assert "validated_calls" not in patch or patch["validated_calls"] == []
    # Un ToolMessage d'erreur est injecté
    assert "messages" in patch
    msgs = patch["messages"]
    assert all(isinstance(m, ToolMessage) for m in msgs)
    # Le content est un JSON parseable avec error/details
    payload = json.loads(msgs[0].content)
    assert payload["error"] == "validation_failed"
    assert payload["tool"] == "ask_qcu"
    assert "details" in payload
    # retry_count incrémenté
    assert patch.get("retry_count") == 1


@pytest.mark.asyncio
async def test_validate_unknown_tool_emits_error() -> None:
    state = _state_with_call("frobnicate", {"x": 1})
    patch = await node_validate_payload(state)
    assert "errors" in patch
    msgs = patch.get("messages") or []
    assert any(isinstance(m, ToolMessage) for m in msgs)


@pytest.mark.asyncio
async def test_validate_idempotent_on_already_validated() -> None:
    state = _state_with_call(
        "ask_qcu",
        {
            "question": "Q",
            "options": [
                {"value": "a", "label": "A"},
                {"value": "b", "label": "B"},
            ],
        },
    )
    # Premier passage
    patch1 = await node_validate_payload(state)
    # Reconstruire l'état avec le validated
    state2 = state.model_copy(update={"validated_calls": patch1["validated_calls"]})
    patch2 = await node_validate_payload(state2)
    # Pas de re-validation
    assert patch2 == {}


def test_has_unvalidated_calls_true() -> None:
    state = _state_with_call("ask_qcu", {"question": "Q", "options": []})
    assert has_unvalidated_calls(state) is True


def test_has_unvalidated_calls_false_when_empty() -> None:
    state = AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/"),
    )
    assert has_unvalidated_calls(state) is False


def test_has_pending_validation_failure_false_on_empty() -> None:
    state = AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/"),
    )
    assert has_pending_validation_failure(state) is False
