"""F56 / T034 — Tests unit du compose_response avec sourcing (mocks settings).

Évite la DB. Vérifie les 4 décisions ; voir les e2e pour le full agent run.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.agent.nodes.compose_response import node_compose_response
from app.agent.sourcing.tool_schemas import CiteSourceArgs
from app.agent.state import AgentState, ContextJson, ValidatedToolCall


def _state(*, text: str, retry_count: int = 0, validated_calls=None) -> AgentState:
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hello",
        context_json=ContextJson(page_route="/chat"),
        llm_response_text=text,
        sourcing_retry_count=retry_count,
        validated_calls=validated_calls or [],
    )


def _settings(mode: str):
    class _S:
        LLM_AGENT_SOURCING_MODE = mode

    return _S()


@pytest.mark.unit
async def test_off_mode_returns_text_directly() -> None:
    state = _state(text="Le seuil est 50 M USD.")
    with patch(
        "app.agent.nodes.compose_response.get_settings", return_value=_settings("off")
    ):
        out = await node_compose_response(state)
    assert out["final_text"] == "Le seuil est 50 M USD."


@pytest.mark.unit
async def test_strict_unsourced_triggers_retry_with_system_message() -> None:
    state = _state(text="Le seuil GCF est 50 M USD.")
    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_settings("strict"),
    ):
        out = await node_compose_response(state)
    assert out["sourcing_decision"] == "retry"
    assert out["sourcing_retry_count"] == 1
    assert "messages" in out
    # Message système d'injection retry
    assert len(out["messages"]) == 1


@pytest.mark.unit
async def test_strict_unsourced_after_retry_triggers_fallback() -> None:
    state = _state(text="Le seuil GCF est 50 M USD.", retry_count=1)
    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_settings("strict"),
    ):
        out = await node_compose_response(state)
    assert out["sourcing_decision"] == "fallback"
    assert "Je ne dispose pas de source vérifiée" in out["final_text"]


@pytest.mark.unit
async def test_strict_with_cite_source_passes() -> None:
    call = ValidatedToolCall(
        id=str(uuid4()),
        name="cite_source",
        arguments=CiteSourceArgs(source_id=uuid4()),
    )
    state = _state(text="Le seuil GCF est 50 M USD.", validated_calls=[call])
    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_settings("strict"),
    ):
        out = await node_compose_response(state)
    assert out["sourcing_decision"] == "accept"
    assert out["final_text"] == "Le seuil GCF est 50 M USD."


@pytest.mark.unit
async def test_permissive_mode_annotates_without_blocking() -> None:
    state = _state(text="Le seuil GCF est 50 M USD.")
    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_settings("permissive"),
    ):
        out = await node_compose_response(state)
    assert out["sourcing_decision"] == "annotate"
    assert out["final_text"] == "Le seuil GCF est 50 M USD."


@pytest.mark.unit
async def test_empty_text_returns_empty() -> None:
    state = _state(text="")
    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_settings("strict"),
    ):
        out = await node_compose_response(state)
    assert out["final_text"] == ""


@pytest.mark.unit
async def test_chat_message_sources_aggregated_on_accept() -> None:
    sid = uuid4()
    call = ValidatedToolCall(
        id=str(uuid4()),
        name="cite_source",
        arguments=CiteSourceArgs(source_id=sid),
    )
    state = _state(text="Le seuil GCF est 50 M USD.", validated_calls=[call])
    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_settings("strict"),
    ):
        out = await node_compose_response(state)
    assert out["sourcing_decision"] == "accept"
    assert "chat_message_sources" in out
    sources = out["chat_message_sources"]
    assert len(sources) == 1
    assert sources[0]["source_id"] == str(sid)
    assert sources[0]["citation_index"] == 1
