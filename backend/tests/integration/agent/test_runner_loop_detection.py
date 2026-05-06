"""F58 / US7 — Tests du wiring loop_detector dans validate_payload.

Vérifie que :
- 3x ``create_project`` avec mêmes arguments → ``loop_detected = True``
  + AgentError ``code='loop_detected'`` non retriable.
- 3x ``cite_source`` avec arguments différents → pas de loop_detected.
- compose_response émet le message FR ``Boucle détectée`` quand
  ``loop_detected`` est dans les errors.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from app.agent.nodes.compose_response import node_compose_response
from app.agent.nodes.validate_payload import node_validate_payload
from app.agent.state import (
    AgentError,
    AgentState,
    ContextJson,
    ToolCall,
    ValidatedToolCall,
)
from app.orchestrator.tool_registry import TOOL_REGISTRY, tool


def _ensure_dummy_tool() -> None:
    """Enregistre un tool dummy pour le test (idempotent)."""

    class _Args(BaseModel):
        model_config = ConfigDict(extra="forbid")

        name: str
        region: str

    if "dummy_loop_tool" not in TOOL_REGISTRY:
        tool(
            name="dummy_loop_tool",
            description="Dummy tool for loop detection tests",
            use_when="never",
            dont_use_when="always",
            schema=_Args,
        )


def _state(*, tool_calls: list[ToolCall], validated_calls=None) -> AgentState:
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hello",
        context_json=ContextJson(page_route="/chat"),
        tool_calls=tool_calls,
        validated_calls=validated_calls or [],
    )


@pytest.mark.integration
async def test_loop_detected_after_3_identical_calls() -> None:
    """validate_payload retourne loop_detected=True quand 3x mêmes args."""
    _ensure_dummy_tool()

    args = {"name": "loopy", "region": "CI"}
    args_model = TOOL_REGISTRY["dummy_loop_tool"].schema(**args)

    # 2 appels validés précédemment + 1 nouveau identique → 3ᵉ identique
    validated = [
        ValidatedToolCall(id=f"tc{i}", name="dummy_loop_tool", arguments=args_model)
        for i in range(2)
    ]
    pending = [ToolCall(id="tc3", name="dummy_loop_tool", arguments=args)]

    state = _state(tool_calls=pending, validated_calls=validated)
    out = await node_validate_payload(state)

    assert out.get("loop_detected") is True
    errors = out.get("errors", [])
    assert len(errors) == 1
    assert errors[0].code == "loop_detected"
    assert errors[0].retriable is False


@pytest.mark.integration
async def test_no_loop_when_args_differ() -> None:
    """3x cite_source avec args différents → pas de loop."""
    _ensure_dummy_tool()

    schema = TOOL_REGISTRY["dummy_loop_tool"].schema
    validated = [
        ValidatedToolCall(
            id=f"tc{i}",
            name="dummy_loop_tool",
            arguments=schema(name=f"diff_{i}", region="CI"),
        )
        for i in range(2)
    ]
    pending = [
        ToolCall(id="tc3", name="dummy_loop_tool", arguments={"name": "diff_X", "region": "SN"})
    ]

    state = _state(tool_calls=pending, validated_calls=validated)
    out = await node_validate_payload(state)

    assert out.get("loop_detected", False) is False


@pytest.mark.integration
async def test_too_many_calls_per_turn_triggers_loop() -> None:
    """11ᵉ tool call dans le même tour → loop_detected (cap absolu)."""
    _ensure_dummy_tool()

    schema = TOOL_REGISTRY["dummy_loop_tool"].schema
    validated = [
        ValidatedToolCall(
            id=f"tc{i}",
            name="dummy_loop_tool",
            arguments=schema(name=f"u_{i}", region="CI"),
        )
        for i in range(10)
    ]
    pending = [ToolCall(id="tc11", name="dummy_loop_tool", arguments={"name": "u_11", "region": "CI"})]

    state = _state(tool_calls=pending, validated_calls=validated)
    out = await node_validate_payload(state)

    assert out.get("loop_detected") is True
    errors = out.get("errors", [])
    assert errors[0].details["reason"] == "too_many_calls"


@pytest.mark.integration
async def test_compose_response_emits_french_loop_message() -> None:
    """compose_response sort un message FR clair quand loop_detected."""
    state = AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="…",
        context_json=ContextJson(page_route="/chat"),
        llm_response_text="",
        errors=[
            AgentError(
                node_name="validate_payload",
                code="loop_detected",
                message="Boucle détectée (identical_args_3x) sur create_project",
                retriable=False,
                details={"tool_name": "create_project", "reason": "identical_args_3x"},
            )
        ],
    )

    class _SP:
        LLM_AGENT_SOURCING_MODE = "permissive"

    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_SP(),
    ):
        out = await node_compose_response(state)

    assert "boucle" in out["final_text"].lower()
    assert out.get("loop_detected") is True
