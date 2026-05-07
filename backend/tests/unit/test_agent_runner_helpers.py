"""Tests unitaires des helpers internes du runner — pas d'I/O DB.

Couvre :
- ``_coerce_to_state`` (dict/AgentState/fallback) ;
- ``_emit_events`` avec validation_error, llm_response_text, dispatch_results ;
- ``_aggregate_step_metrics`` exception path (best-effort) ;
- branches de préparation ``context_json`` dans ``run_agent``.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.runner import (
    _aggregate_step_metrics,
    _coerce_to_state,
    _emit_events,
    make_thread_id,
)
from app.agent.state import (
    AgentError,
    AgentState,
    ContextJson,
    DispatchCategory,
    ToolDispatchResult,
)


def _make_initial_state() -> AgentState:
    aid = uuid4()
    uid = uuid4()
    return AgentState(
        thread_id=f"{aid}:{uuid4()}",
        account_id=aid,
        user_id=uid,
        user_message="bonjour",
        context_json=ContextJson(page_route="/"),
    )


# ---------------------------------------------------------------------------
# _coerce_to_state
# ---------------------------------------------------------------------------


def test_coerce_to_state_passthrough_agent_state() -> None:
    s = _make_initial_state()
    out = _coerce_to_state(s, fallback=s)
    assert out is s


def test_coerce_to_state_dict_merges_with_fallback() -> None:
    s = _make_initial_state()
    patch = {"final_text": "merged"}
    out = _coerce_to_state(patch, fallback=s)
    assert out.final_text == "merged"
    assert out.thread_id == s.thread_id


def test_coerce_to_state_invalid_input_returns_fallback() -> None:
    s = _make_initial_state()
    # Une string n'est ni AgentState ni dict → retourne fallback.
    out = _coerce_to_state("garbage", fallback=s)
    assert out is s


# ---------------------------------------------------------------------------
# make_thread_id
# ---------------------------------------------------------------------------


def test_make_thread_id_with_explicit_conv_id() -> None:
    aid = uuid4()
    cid = uuid4()
    tid = make_thread_id(aid, cid)
    assert tid == f"{aid}:{cid}"


def test_make_thread_id_generates_conv_id_if_none() -> None:
    aid = uuid4()
    tid = make_thread_id(aid)
    assert tid.startswith(f"{aid}:")
    assert len(tid) == 73  # 36 + ':' + 36


# ---------------------------------------------------------------------------
# _emit_events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_events_validation_retry_and_token_and_dispatch() -> None:
    s = _make_initial_state()
    s.errors.append(
        AgentError(
            node_name="validate_payload",
            code="validation_error",
            message="bad arg",
            details={"tool_name": "ask_qcu", "tool_call_id": "call-1"},
            retriable=True,
        )
    )
    s.llm_response_text = "Hello"
    s.dispatch_results.append(
        ToolDispatchResult(
            tool_call_id="call-2",
            tool_name="ask_qcu",
            category=DispatchCategory.SSE_ONLY,
            status="ok",
            kind="frontend_event",
            output={"question": "?", "options": []},
        )
    )

    lines = []
    async for line in _emit_events(s, run_id=None):
        lines.append(line)

    flat = "\n".join(lines)
    assert "validation_retry" in flat
    assert "Hello" in flat
    # tool_invoke event from dispatch_result
    assert "tool_invoke" in flat


@pytest.mark.asyncio
async def test_emit_events_no_errors_yields_only_token() -> None:
    s = _make_initial_state()
    s.llm_response_text = "Bonjour"
    lines = []
    async for line in _emit_events(s, run_id=None):
        lines.append(line)
    flat = "\n".join(lines)
    assert "Bonjour" in flat
    assert "validation_retry" not in flat


# ---------------------------------------------------------------------------
# _aggregate_step_metrics — best-effort exception path
# ---------------------------------------------------------------------------


def test_aggregate_step_metrics_returns_none_on_exception() -> None:
    """Si la session lève une exception, la fonction retourne (None, None, None)."""

    class ExplodingSession:
        def execute(self, *_a, **_kw):  # noqa: ARG002
            raise RuntimeError("DB exploded")

    ti, to, fn = _aggregate_step_metrics(
        ExplodingSession(), run_id=uuid4()
    )  # type: ignore[arg-type]
    assert ti is None
    assert to is None
    assert fn is None


# ---------------------------------------------------------------------------
# Branches de préparation context_json (via run_agent — sans DB).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_agent_thread_access_denied_on_invalid_format() -> None:
    """Un thread_id mal formé doit lever ``ThreadAccessDenied``."""
    from app.agent.runner import ThreadAccessDenied, run_agent

    gen = run_agent(
        account_id=uuid4(),
        user_id=uuid4(),
        thread_id="not-a-valid-thread-id",
        user_message="bonjour",
        context_json={"page_route": "/"},
    )
    with pytest.raises(ThreadAccessDenied):
        async for _ in gen:
            pass


@pytest.mark.asyncio
async def test_run_agent_thread_access_denied_on_cross_tenant_prefix() -> None:
    """Un thread_id avec un account UUID qui ne matche pas l'``account_id``
    fourni doit lever ``ThreadAccessDenied`` (404 silencieux, P2)."""
    from app.agent.runner import ThreadAccessDenied, run_agent

    aid = uuid4()
    other = uuid4()
    tid = f"{other}:{uuid4()}"  # mismatch préfixe

    gen = run_agent(
        account_id=aid,
        user_id=uuid4(),
        thread_id=tid,
        user_message="bonjour",
        context_json={"page_route": "/"},
    )
    with pytest.raises(ThreadAccessDenied):
        async for _ in gen:
            pass


