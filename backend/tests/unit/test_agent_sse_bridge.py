"""F53 / T038 — Tests unitaires pour ``app/agent/sse_bridge.py``."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.agent.sse_bridge import (
    SseEvent,
    make_done_event,
    make_error_event,
    make_mutation_event,
    make_token_event,
    make_tool_invoke_event,
    make_validation_retry_event,
    map_dispatch_to_sse,
)
from app.agent.state import DispatchCategory, ToolDispatchResult

pytestmark = pytest.mark.unit


def _parse_sse(s: str) -> tuple[str, dict]:
    """Helper : parse un payload SSE en (event_type, data)."""
    lines = s.strip().split("\n")
    event_type = ""
    data_raw = ""
    for line in lines:
        if line.startswith("event:"):
            event_type = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_raw = line.split(":", 1)[1].strip()
    return event_type, json.loads(data_raw) if data_raw else {}


class TestSseEvent:
    def test_serialize_format(self) -> None:
        ev = SseEvent(event_type="x", data={"a": 1})
        s = ev.serialize()
        assert s.startswith("event: x\n")
        assert "data: " in s
        assert s.endswith("\n\n")


class TestTokenEvent:
    def test_token_event(self) -> None:
        ev = make_token_event("hello")
        et, data = _parse_sse(ev.serialize())
        assert et == "token"
        assert data == {"text": "hello"}


class TestToolInvokeEvent:
    def test_tool_invoke_event(self) -> None:
        result = ToolDispatchResult(
            tool_call_id="c1",
            tool_name="ask_qcu",
            category=DispatchCategory.SSE_ONLY,
            status="ok",
            output={"arguments": {"q": "Q?"}},
        )
        ev = make_tool_invoke_event(result)
        et, data = _parse_sse(ev.serialize())
        assert et == "tool_invoke"
        assert data["tool_call_id"] == "c1"
        assert data["tool_name"] == "ask_qcu"
        assert data["arguments"] == {"q": "Q?"}


class TestMutationEvent:
    def test_mutation_event(self) -> None:
        result = ToolDispatchResult(
            tool_call_id="c2",
            tool_name="create_projet",
            category=DispatchCategory.DB_MUTATION,
            status="ok",
            output={"id": "p123"},
        )
        audit_id = uuid4()
        ev = make_mutation_event(result, audit_log_id=audit_id)
        et, data = _parse_sse(ev.serialize())
        assert et == "mutation"
        assert data["snapshot"] == {"id": "p123"}
        assert data["audit_log_id"] == str(audit_id)


class TestValidationRetryEvent:
    def test_validation_retry_event(self) -> None:
        ev = make_validation_retry_event(
            retry_count=1,
            tool_name="create_projet",
            error_summary="field 'severity' not in enum",
        )
        et, data = _parse_sse(ev.serialize())
        assert et == "validation_retry"
        assert data["retry_count"] == 1
        assert data["tool_name"] == "create_projet"
        assert "severity" in data["error_summary"]

    def test_error_summary_truncated(self) -> None:
        ev = make_validation_retry_event(
            retry_count=1,
            tool_name="x",
            error_summary="a" * 1000,
        )
        et, data = _parse_sse(ev.serialize())
        assert len(data["error_summary"]) <= 500


class TestErrorEvent:
    def test_error_event(self) -> None:
        rid = uuid4()
        ev = make_error_event(code="timeout", message="too slow", agent_run_id=rid)
        et, data = _parse_sse(ev.serialize())
        assert et == "error"
        assert data["code"] == "timeout"
        assert data["message"] == "too slow"
        assert data["agent_run_id"] == str(rid)

    def test_error_event_without_run_id(self) -> None:
        ev = make_error_event(code="x", message="y", agent_run_id=None)
        et, data = _parse_sse(ev.serialize())
        assert data["agent_run_id"] is None


class TestDoneEvent:
    def test_done_event_minimal(self) -> None:
        ev = make_done_event(final_text="ok")
        et, data = _parse_sse(ev.serialize())
        assert et == "done"
        assert data["final_text"] == "ok"
        assert data["tokens_used"] is None

    def test_done_event_with_tokens(self) -> None:
        ev = make_done_event(final_text="x", tokens_in=100, tokens_out=50)
        et, data = _parse_sse(ev.serialize())
        assert data["tokens_used"] == {"in": 100, "out": 50}


class TestMapDispatchToSse:
    def test_sse_only_maps_to_tool_invoke(self) -> None:
        result = ToolDispatchResult(
            tool_call_id="c1",
            tool_name="ask_qcu",
            category=DispatchCategory.SSE_ONLY,
            status="ok",
        )
        ev = map_dispatch_to_sse(result)
        assert ev is not None
        assert ev.event_type == "tool_invoke"

    def test_db_mutation_maps_to_mutation(self) -> None:
        result = ToolDispatchResult(
            tool_call_id="c2",
            tool_name="create_projet",
            category=DispatchCategory.DB_MUTATION,
            status="ok",
        )
        ev = map_dispatch_to_sse(result)
        assert ev is not None
        assert ev.event_type == "mutation"

    def test_reinvoke_returns_none(self) -> None:
        result = ToolDispatchResult(
            tool_call_id="c3",
            tool_name="recall_history",
            category=DispatchCategory.REINVOKE_LLM,
            status="ok",
        )
        ev = map_dispatch_to_sse(result)
        assert ev is None

    def test_error_status_returns_none(self) -> None:
        result = ToolDispatchResult(
            tool_call_id="c4",
            tool_name="ask_qcu",
            category=DispatchCategory.SSE_ONLY,
            status="error",
        )
        ev = map_dispatch_to_sse(result)
        assert ev is None
