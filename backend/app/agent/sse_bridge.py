"""F53 / T038 — Mapping LangGraph events → SSE events.

Le frontend (F41) consomme déjà ``token``, ``error``, ``done`` (F13). F53
ajoute ``tool_invoke``, ``mutation``, ``validation_retry`` (specs SSE
``contracts/sse-events.md``). F55 polishera la cohérence finale.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.agent.state import DispatchCategory, ToolDispatchResult


@dataclass(frozen=True)
class SseEvent:
    """Représentation simple d'un event SSE (event_type + json_payload)."""

    event_type: str
    data: dict[str, Any]

    def serialize(self) -> str:
        """Sérialise au format SSE ``event: type\\ndata: json\\n\\n``."""
        return (
            f"event: {self.event_type}\n"
            f"data: {json.dumps(self.data, ensure_ascii=False)}\n\n"
        )


def make_token_event(text: str) -> SseEvent:
    return SseEvent(event_type="token", data={"text": text})


def make_tool_invoke_event(result: ToolDispatchResult) -> SseEvent:
    """SSE ``tool_invoke`` pour ``ask_*``/``show_*`` (FR-007 a)."""
    out = result.output or {}
    return SseEvent(
        event_type="tool_invoke",
        data={
            "tool_call_id": result.tool_call_id,
            "tool_name": result.tool_name,
            "arguments": out.get("arguments", {}),
        },
    )


def make_mutation_event(
    result: ToolDispatchResult,
    *,
    audit_log_id: UUID | None = None,
) -> SseEvent:
    """SSE ``mutation`` pour les ``update_*``/``create_*``/``delete_*`` réussis."""
    out = result.output or {}
    payload = {
        "tool_call_id": result.tool_call_id,
        "tool_name": result.tool_name,
        "snapshot": out,
        "audit_log_id": str(audit_log_id) if audit_log_id else None,
    }
    return SseEvent(event_type="mutation", data=payload)


def make_validation_retry_event(
    *,
    retry_count: int,
    tool_name: str,
    error_summary: str,
) -> SseEvent:
    return SseEvent(
        event_type="validation_retry",
        data={
            "retry_count": retry_count,
            "tool_name": tool_name,
            "error_summary": error_summary[:500],
        },
    )


def make_error_event(*, code: str, message: str, agent_run_id: UUID | None = None) -> SseEvent:
    return SseEvent(
        event_type="error",
        data={
            "code": code,
            "message": message,
            "agent_run_id": str(agent_run_id) if agent_run_id else None,
        },
    )


def make_done_event(
    *,
    final_text: str,
    agent_run_id: UUID | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> SseEvent:
    return SseEvent(
        event_type="done",
        data={
            "final_text": final_text,
            "agent_run_id": str(agent_run_id) if agent_run_id else None,
            "tokens_used": (
                {"in": tokens_in, "out": tokens_out}
                if (tokens_in is not None or tokens_out is not None)
                else None
            ),
        },
    )


def map_dispatch_to_sse(
    result: ToolDispatchResult,
) -> SseEvent | None:
    """Mappe un ``ToolDispatchResult`` vers un SSE event (si applicable).

    - SSE_ONLY → ``tool_invoke``
    - DB_MUTATION (status=ok) → ``mutation``
    - REINVOKE_LLM → None (pas d'event front)
    """
    if result.status != "ok":
        return None
    if result.category == DispatchCategory.SSE_ONLY:
        return make_tool_invoke_event(result)
    if result.category == DispatchCategory.DB_MUTATION:
        return make_mutation_event(result)
    return None


__all__ = [
    "SseEvent",
    "make_done_event",
    "make_error_event",
    "make_mutation_event",
    "make_token_event",
    "make_tool_invoke_event",
    "make_validation_retry_event",
    "map_dispatch_to_sse",
]
