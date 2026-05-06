"""F53 / T036 — Tests unitaires pour ``app/agent/nodes/compose_response.py``."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.nodes.compose_response import node_compose_response
from app.agent.state import (
    AgentError,
    AgentState,
    ContextJson,
    DispatchCategory,
    ToolDispatchResult,
)

pytestmark = pytest.mark.unit


def _state(**overrides) -> AgentState:
    base = {
        "thread_id": f"{uuid4()}:{uuid4()}",
        "account_id": uuid4(),
        "user_id": uuid4(),
        "user_message": "hi",
        "context_json": ContextJson(page_route="/"),
    }
    base.update(overrides)
    return AgentState(**base)


@pytest.mark.asyncio
async def test_compose_uses_llm_text_when_present() -> None:
    state = _state(llm_response_text="Bonjour, voici la réponse.")
    patch = await node_compose_response(state)
    assert patch["final_text"] == "Bonjour, voici la réponse."


@pytest.mark.asyncio
async def test_compose_fallback_on_unrecoverable_validation_error() -> None:
    state = _state(
        llm_response_text="",
        errors=[
            AgentError(
                node_name="validate_payload",
                code="validation_error",
                message="invalid",
                retriable=False,
            )
        ],
    )
    patch = await node_compose_response(state)
    assert "n'arrive pas" in patch["final_text"].lower()


@pytest.mark.asyncio
async def test_compose_empty_when_dispatch_only() -> None:
    state = _state(
        llm_response_text="",
        dispatch_results=[
            ToolDispatchResult(
                tool_call_id="x",
                tool_name="ask_qcu",
                category=DispatchCategory.SSE_ONLY,
                status="ok",
            )
        ],
    )
    patch = await node_compose_response(state)
    # Texte vide acceptable : la bottom sheet porte l'UX
    assert patch["final_text"] == ""


@pytest.mark.asyncio
async def test_compose_empty_default() -> None:
    state = _state()
    patch = await node_compose_response(state)
    assert patch["final_text"] == ""
