"""F53 / T024 — Tests unitaires pour ``app/agent/tracing.py``.

Aucune écriture DB réelle : on mocke ``record_step``.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.agent.tracing import TraceContext, traced_node

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_traced_node_writes_step_on_success(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_record_step(session, **kwargs):
        calls.append(kwargs)
        return uuid4()

    monkeypatch.setattr("app.agent.tracing.record_step", fake_record_step)

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=MagicMock(),
        trace_mode="db",
    )
    async with traced_node(ctx, node_name="route"):
        pass

    assert len(calls) == 1
    assert calls[0]["node_name"] == "route"
    assert calls[0]["status"] == "ok"
    assert calls[0]["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_traced_node_writes_step_on_error(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_record_step(session, **kwargs):
        calls.append(kwargs)
        return uuid4()

    monkeypatch.setattr("app.agent.tracing.record_step", fake_record_step)

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=MagicMock(),
        trace_mode="db",
    )
    with pytest.raises(ValueError):
        async with traced_node(ctx, node_name="route"):
            raise ValueError("boom")

    assert len(calls) == 1
    assert calls[0]["status"] == "error"
    assert calls[0]["error"] == "boom"


@pytest.mark.asyncio
async def test_traced_node_skips_db_when_off(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_record_step(session, **kwargs):
        calls.append(kwargs)
        return uuid4()

    monkeypatch.setattr("app.agent.tracing.record_step", fake_record_step)

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=MagicMock(),
        trace_mode="off",
    )
    async with traced_node(ctx, node_name="route"):
        pass

    assert calls == []


@pytest.mark.asyncio
async def test_traced_node_skips_when_no_session(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_record_step(session, **kwargs):
        calls.append(kwargs)
        return uuid4()

    monkeypatch.setattr("app.agent.tracing.record_step", fake_record_step)

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=None,
        trace_mode="db",
    )
    async with traced_node(ctx, node_name="route"):
        pass

    assert calls == []


@pytest.mark.asyncio
async def test_traced_node_swallows_db_write_failure(monkeypatch) -> None:
    """Le tracing ne MUST jamais casser le run."""

    def boom(session, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr("app.agent.tracing.record_step", boom)

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=MagicMock(),
        trace_mode="db",
    )
    # Doit s'exécuter sans lever
    async with traced_node(ctx, node_name="route"):
        pass


@pytest.mark.asyncio
async def test_traced_node_timeout_status(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_record_step(session, **kwargs):
        calls.append(kwargs)
        return uuid4()

    monkeypatch.setattr("app.agent.tracing.record_step", fake_record_step)

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=MagicMock(),
        trace_mode="db",
    )
    with pytest.raises(TimeoutError):
        async with traced_node(ctx, node_name="call_llm"):
            raise TimeoutError("slow LLM")

    assert calls[0]["status"] == "timeout"
