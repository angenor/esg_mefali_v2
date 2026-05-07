"""Tests unitaires des helpers de tracing — pas d'I/O DB.

Couvre les chemins :
- ``_extract_usage_from_patch`` (graph.py) avec patches divers ;
- ``_make_traced_node`` no-op si ``agent_run_id`` est None ou si le mode
  est ``off`` ;
- ``traced_node`` (tracing.py) en mode ``off`` (skip DB), mode ``db+stdout``,
  et propagation d'exception.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import _extract_usage_from_patch, _make_traced_node
from app.agent.tracing import StepCounters, TraceContext, traced_node

# ---------------------------------------------------------------------------
# _extract_usage_from_patch
# ---------------------------------------------------------------------------


def test_extract_usage_from_patch_no_dict_returns_none() -> None:
    assert _extract_usage_from_patch(None) == (None, None)
    assert _extract_usage_from_patch("string") == (None, None)
    assert _extract_usage_from_patch(42) == (None, None)


def test_extract_usage_from_patch_empty_messages() -> None:
    assert _extract_usage_from_patch({}) == (None, None)
    assert _extract_usage_from_patch({"messages": []}) == (None, None)


def test_extract_usage_from_patch_skips_non_ai_messages() -> None:
    patch = {"messages": [HumanMessage(content="hi")]}
    assert _extract_usage_from_patch(patch) == (None, None)


def test_extract_usage_from_patch_no_usage_metadata() -> None:
    patch = {"messages": [AIMessage(content="hello")]}
    assert _extract_usage_from_patch(patch) == (None, None)


def test_extract_usage_from_patch_extracts_tokens() -> None:
    msg = AIMessage(
        content="hi",
        usage_metadata={
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
    )
    ti, to = _extract_usage_from_patch({"messages": [msg]})
    assert ti == 10
    assert to == 5


def test_extract_usage_from_patch_sums_multiple() -> None:
    msg1 = AIMessage(
        content="a",
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )
    msg2 = AIMessage(
        content="b",
        usage_metadata={"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
    )
    ti, to = _extract_usage_from_patch({"messages": [msg1, msg2]})
    assert ti == 17
    assert to == 8


# ---------------------------------------------------------------------------
# _make_traced_node — no-op paths (no DB I/O needed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_make_traced_node_noop_when_run_id_none() -> None:
    """Si state.agent_run_id is None, le wrapper exécute le node directement."""
    calls = {"count": 0}

    async def fake_node(state):  # noqa: ARG001
        calls["count"] += 1
        return {"foo": "bar"}

    wrapped = _make_traced_node(fake_node, "fake")

    class FakeState:
        agent_run_id = None
        account_id = None

    result = await wrapped(FakeState())  # type: ignore[arg-type]
    assert result == {"foo": "bar"}
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_make_traced_node_noop_when_trace_mode_off(monkeypatch) -> None:
    """Si LLM_AGENT_TRACE='off', le wrapper exécute le node directement."""
    from uuid import uuid4

    monkeypatch.setattr("app.agent.graph.get_trace_mode", lambda: "off")

    async def fake_node(state):  # noqa: ARG001
        return {"messages": [AIMessage(content="x")]}

    wrapped = _make_traced_node(fake_node, "fake")

    class FakeState:
        agent_run_id = uuid4()
        account_id = uuid4()

    result = await wrapped(FakeState())  # type: ignore[arg-type]
    # Pas d'exception — exécution directe.
    assert "messages" in result


# ---------------------------------------------------------------------------
# traced_node — paths sans session DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_traced_node_skips_db_write_when_session_none() -> None:
    """Si ctx.session est None, ``record_step`` n'est pas appelé."""
    from uuid import uuid4

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=None,
        trace_mode="db",
    )
    async with traced_node(ctx, node_name="x") as counters:
        counters.tokens_in = 5
    # last_node_name doit être set même sans session.
    assert ctx.last_node_name == "x"
    # Tokens agrégés dans ctx
    assert ctx.total_tokens_in == 5


@pytest.mark.asyncio
async def test_traced_node_skips_db_write_when_run_id_none() -> None:
    from uuid import uuid4

    ctx = TraceContext(
        run_id=None,
        account_id=uuid4(),
        session=object(),  # type: ignore[arg-type]
        trace_mode="db",
    )
    async with traced_node(ctx, node_name="y") as counters:
        counters.tokens_out = 3
    assert ctx.last_node_name == "y"
    assert ctx.total_tokens_out == 3


@pytest.mark.asyncio
async def test_traced_node_propagates_exception(caplog) -> None:
    """Une exception levée dans le bloc est propagée et loggée
    avec status='error'."""
    from uuid import uuid4

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=None,
        trace_mode="off",  # off → pas de write DB → exception simple à observer
    )
    with pytest.raises(RuntimeError, match="boom"):
        async with traced_node(ctx, node_name="z"):
            raise RuntimeError("boom")
    # Le finally a couru → last_node_name set même sur erreur.
    assert ctx.last_node_name == "z"


@pytest.mark.asyncio
async def test_traced_node_propagates_timeout() -> None:
    from uuid import uuid4

    ctx = TraceContext(
        run_id=uuid4(),
        account_id=uuid4(),
        session=None,
        trace_mode="off",
    )
    with pytest.raises(TimeoutError):
        async with traced_node(ctx, node_name="z"):
            raise TimeoutError("slow")
    assert ctx.last_node_name == "z"


def test_step_counters_defaults() -> None:
    c = StepCounters()
    assert c.tokens_in is None
    assert c.tokens_out is None
    assert c.tool_calls_count == 0
    assert c.extras == {}
