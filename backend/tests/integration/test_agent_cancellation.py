"""F53 / T078-T079 — Tests d'annulation côté client (US8 / SC-007)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.agent.runner import run_agent
from tests.agent_fixtures import FakeLLM, make_text_response

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_runner_handles_cancellation(monkeypatch) -> None:
    """Si le consumer SSE annule, le runner doit propager CancelledError."""
    fake = FakeLLM(responses=[make_text_response("hello")])
    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: fake
    )

    a = uuid4()
    tid = f"{a}:{uuid4()}"

    async def consume_partial():
        gen = run_agent(
            account_id=a,
            user_id=uuid4(),
            thread_id=tid,
            user_message="hi",
            context_json={"page_route": "/"},
        )
        # Cancel après le premier yield
        async for _line in gen:
            await gen.aclose()
            break

    # Doit s'exécuter sans crasher (CancelledError est attendu mais pas levé
    # vers le test grâce à aclose)
    await consume_partial()


@pytest.mark.asyncio
async def test_runner_timeout_emits_error(monkeypatch) -> None:
    """Sur dépassement de LLM_AGENT_TIMEOUT_S, un event ``error`` timeout est émis."""
    from types import SimpleNamespace

    class SlowGraph:
        async def ainvoke(self, state):
            await asyncio.sleep(10)
            return state

    a = uuid4()
    tid = f"{a}:{uuid4()}"

    fake_settings = SimpleNamespace(
        LLM_AGENT_MODE="langgraph",
        LLM_AGENT_TIMEOUT_S=0.1,
        LLM_AGENT_MAX_RETRIES=2,
        LLM_AGENT_MAX_TOOLS=10,
        LLM_AGENT_TRACE="off",
    )
    monkeypatch.setattr("app.agent.runner.get_settings", lambda: fake_settings)

    seen_error = False
    async for line in run_agent(
        account_id=a,
        user_id=uuid4(),
        thread_id=tid,
        user_message="slow",
        compiled_graph=SlowGraph(),
    ):
        if "event: error" in line and "timeout" in line.lower():
            seen_error = True
            break
    assert seen_error, "An error event with code 'timeout' must be emitted"


@pytest.mark.asyncio
async def test_runner_cancelled_propagates_clean(monkeypatch) -> None:
    """Si CancelledError est levé pendant le graph, le runner ne MUST PAS
    persister un message assistant tronqué."""

    persisted: list = []

    def fake_persist(*args, **kwargs):
        persisted.append(kwargs.get("content"))

    monkeypatch.setattr(
        "app.agent.runner._persist_assistant", fake_persist
    )

    class CancellingGraph:
        async def ainvoke(self, state):
            raise asyncio.CancelledError()

    a = uuid4()
    tid = f"{a}:{uuid4()}"

    with pytest.raises(asyncio.CancelledError):
        async for _line in run_agent(
            account_id=a,
            user_id=uuid4(),
            thread_id=tid,
            user_message="hi",
            compiled_graph=CancellingGraph(),
        ):
            pass

    # Aucune persistance ne doit avoir eu lieu
    assert persisted == []
