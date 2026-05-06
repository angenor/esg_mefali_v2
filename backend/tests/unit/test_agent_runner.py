"""F53 — Tests unitaires (légers) pour ``app/agent/runner.py``.

Couvre les helpers + les chemins de validation thread_id/cross-tenant qui
n'exigent pas de DB.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.runner import (
    ThreadAccessDenied,
    _coerce_to_state,
    make_thread_id,
    run_agent,
)
from app.agent.state import AgentState, ContextJson

pytestmark = pytest.mark.unit


def test_make_thread_id_format() -> None:
    a = uuid4()
    c = uuid4()
    tid = make_thread_id(a, c)
    assert tid == f"{a}:{c}"


def test_make_thread_id_generates_conv() -> None:
    a = uuid4()
    tid = make_thread_id(a)
    prefix, _, conv = tid.partition(":")
    assert prefix == str(a)
    assert len(conv) == 36


def test_coerce_to_state_passes_through() -> None:
    fallback = AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/"),
    )
    assert _coerce_to_state(fallback, fallback=fallback) is fallback


def test_coerce_to_state_from_dict() -> None:
    a = uuid4()
    u = uuid4()
    d = {
        "thread_id": f"{a}:{uuid4()}",
        "account_id": a,
        "user_id": u,
        "user_message": "hi",
        "context_json": ContextJson(page_route="/"),
        "final_text": "from dict",
    }
    fallback = AgentState(
        thread_id=f"{a}:{uuid4()}",
        account_id=a,
        user_id=u,
        user_message="ignored",
        context_json=ContextJson(page_route="/"),
    )
    result = _coerce_to_state(d, fallback=fallback)
    assert result.final_text == "from dict"


def test_coerce_to_state_invalid_falls_back() -> None:
    fallback = AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/"),
    )
    result = _coerce_to_state(42, fallback=fallback)
    assert result is fallback


@pytest.mark.asyncio
async def test_run_agent_invalid_thread_format_raises() -> None:
    with pytest.raises(ThreadAccessDenied):
        async for _ in run_agent(
            account_id=uuid4(),
            user_id=uuid4(),
            thread_id="not-valid",
            user_message="hi",
        ):
            pass


@pytest.mark.asyncio
async def test_run_agent_cross_tenant_raises() -> None:
    a = uuid4()
    b = uuid4()
    cross_tid = f"{a}:{uuid4()}"
    with pytest.raises(ThreadAccessDenied):
        async for _ in run_agent(
            account_id=b,
            user_id=uuid4(),
            thread_id=cross_tid,
            user_message="hi",
        ):
            pass
