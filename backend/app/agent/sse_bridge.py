"""F53/F55 — Mapping LangGraph events → SSE events.

Le frontend (F41) consomme ``token``, ``error``, ``done`` (F13). F53 a ajouté
``tool_invoke``, ``mutation``, ``validation_retry``. F55 enrichit avec
``text_delta`` (streaming token-par-token), ``tool_call_completed``
(admin only), et le préfixe ``dry_run:`` (US6).

Référence : ``specs/055-agent-tool-dispatch-sse/contracts/sse-events.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.agent.sse import format_event
from app.agent.state import DispatchCategory, ToolCategory, ToolDispatchResult


@dataclass(frozen=True)
class SseEvent:
    """Représentation simple d'un event SSE (event_type + json_payload)."""

    event_type: str
    data: dict[str, Any]
    dry_run: bool = False
    event_id: str | None = None

    def serialize(self) -> str:
        """Sérialise au format SSE conforme contract F55."""
        return format_event(
            self.event_type,
            self.data,
            event_id=self.event_id,
            dry_run=self.dry_run,
        )


# F56 — Liste blanche des event_type acceptés par le bridge SSE.
# Utilisée par l'event_bus_publisher pour valider qu'un event est connu
# avant émission (les events inconnus sont logés en warning et ignorés).
KNOWN_EVENTS: frozenset[str] = frozenset(
    {
        "token",
        "text_delta",
        "tool_call_started",
        "tool_call_completed",
        "tool_invoke",
        "mutation",
        "validation_retry",
        "error",
        "done",
        "message_done",
        # F56 NEW
        "unsourced_claim",
    }
)


def make_unsourced_claim_event(
    *,
    claim: str,
    reason: str,
    thread_id: str | None = None,
    message_id: str | None = None,
    agent_run_id: str | None = None,
    span: tuple[int, int] | None = None,
    unsourced_flag_id: str | None = None,
    auto: bool = False,
) -> SseEvent:
    """F56 — Builder pour l'event ``unsourced_claim`` (FR-005)."""
    return SseEvent(
        event_type="unsourced_claim",
        data={
            "thread_id": thread_id,
            "message_id": message_id,
            "agent_run_id": agent_run_id,
            "claim": claim,
            "reason": reason,
            "span": list(span) if span else None,
            "unsourced_flag_id": unsourced_flag_id,
            "auto": auto,
        },
    )


# --- Builders d'events spécifiques -----------------------------------------


def make_token_event(text: str) -> SseEvent:
    """Compat F53/F13 — event ``token`` (texte complet en batch)."""
    return SseEvent(event_type="token", data={"text": text})


def make_text_delta_event(
    delta: str,
    *,
    message_id: str | UUID | None = None,
) -> SseEvent:
    """F55 — event ``text_delta`` (streaming token par token)."""
    return SseEvent(
        event_type="text_delta",
        data={
            "delta": delta,
            "message_id": str(message_id) if message_id else None,
        },
    )


def make_tool_call_started_event(
    *, tool_call_id: str, tool_name: str
) -> SseEvent:
    """F55 — event ``tool_call_started`` (debug, admin only filtré côté front)."""
    return SseEvent(
        event_type="tool_call_started",
        data={"tool_call_id": tool_call_id, "tool_name": tool_name},
    )


def make_tool_invoke_event(
    result: ToolDispatchResult,
    *,
    category: ToolCategory | None = None,
    message_id: str | UUID | None = None,
    dry_run: bool = False,
) -> SseEvent:
    """SSE ``tool_invoke`` pour ASK / SHOW (FR-018)."""
    out = result.output or {}
    cat_str = (
        category.value.upper()
        if category
        else str(out.get("category", "ASK")).upper()
    )
    return SseEvent(
        event_type="tool_invoke",
        data={
            "tool_call_id": result.tool_call_id,
            "tool_name": out.get("tool_name", result.tool_name),
            "category": cat_str,
            "arguments": out.get("arguments", {}),
            "message_id": str(message_id) if message_id else None,
        },
        dry_run=dry_run,
    )


def make_mutation_event(
    result: ToolDispatchResult,
    *,
    audit_log_id: UUID | None = None,
    message_id: str | UUID | None = None,
    dry_run: bool = False,
) -> SseEvent:
    """SSE ``mutation`` post-update DB (FR-018).

    Compat F53/F55 :
    - F55 : ``output={'snapshot': {...}}`` → on lit le snapshot.
    - F53 : ``output={...}`` → on prend output directement comme snapshot.
    """
    out = result.output or {}
    snapshot = out.get("snapshot") if isinstance(out, dict) and "snapshot" in out else out
    payload = {
        "tool_call_id": result.tool_call_id,
        "tool_name": result.tool_name,
        "entity_type": result.entity_type,
        "entity_id": str(result.entity_id) if result.entity_id else None,
        "fields_updated": list(result.fields_updated or []),
        "audit_log_id": (
            str(audit_log_id or result.audit_log_id)
            if (audit_log_id or result.audit_log_id)
            else None
        ),
        "snapshot": snapshot if isinstance(snapshot, dict) else {},
        "message_id": str(message_id) if message_id else None,
    }
    return SseEvent(event_type="mutation", data=payload, dry_run=dry_run)


def make_tool_call_completed_event(
    result: ToolDispatchResult,
    *,
    duration_ms: int | None = None,
    dry_run: bool = False,
) -> SseEvent:
    """F55 — ``tool_call_completed`` admin only (filtré côté frontend)."""
    return SseEvent(
        event_type="tool_call_completed",
        data={
            "tool_call_id": result.tool_call_id,
            "tool_name": result.tool_name,
            "kind": result.kind,
            "status": result.status,
            "duration_ms": duration_ms or result.duration_ms or 0,
        },
        dry_run=dry_run,
    )


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


def make_error_event(
    *,
    code: str,
    message: str,
    agent_run_id: UUID | None = None,
) -> SseEvent:
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
    message_id: str | UUID | None = None,
) -> SseEvent:
    """Event ``done`` (compat F13). Voir aussi ``make_message_done_event``."""
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
            "message_id": str(message_id) if message_id else None,
        },
    )


def make_message_done_event(
    *,
    final_text: str,
    agent_run_id: UUID | None = None,
    message_id: str | UUID | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    dry_run: bool = False,
) -> SseEvent:
    """F55 — ``message_done`` standardisé (contract sse-events.md)."""
    return SseEvent(
        event_type="message_done",
        data={
            "message_id": str(message_id) if message_id else None,
            "agent_run_id": str(agent_run_id) if agent_run_id else None,
            "tokens_used": {
                "in": tokens_in or 0,
                "out": tokens_out or 0,
            },
            "final_text": final_text,
        },
        dry_run=dry_run,
    )


def map_dispatch_to_sse(  # noqa: PLR0911 — explicit branches
    result: ToolDispatchResult,
    *,
    message_id: str | UUID | None = None,
    dry_run: bool = False,
) -> SseEvent | None:
    """Mappe un ``ToolDispatchResult`` vers un SSE event applicable.

    Compat F53 + F55 :
    - F53 (kind=None) : on retombe sur ``category`` + ``status='ok'`` → tool_invoke
      / mutation. Si status != 'ok', retour None (compat).
    - F55 (kind set)  : routage explicite via ``kind``. Errors → SSE error.
    """
    # Mode F55 (kind set) -----------------------------------------------------
    if result.kind == "frontend_event" and result.status in {
        "ok",
        "pending_confirmation",
        "cancelled_by_user",
    }:
        cat = ToolCategory.ASK
        out = result.output or {}
        cat_raw = str(out.get("category", "ASK")).upper()
        if cat_raw == "SHOW":
            cat = ToolCategory.SHOW
        return make_tool_invoke_event(
            result, category=cat, message_id=message_id, dry_run=dry_run
        )
    if result.kind == "mutation_result" and result.status == "ok":
        return make_mutation_event(
            result, message_id=message_id, dry_run=dry_run
        )
    if result.kind == "error" and result.status != "ok":
        return make_error_event(
            code=(
                "rate_limited"
                if result.status == "rate_limited"
                else "dispatch_error"
            ),
            message=result.error_summary or "dispatch_failed",
        )
    if result.kind == "tool_message":
        # Pas d'event SSE, le résultat est ré-injecté en ToolMessage
        return None

    # Mode F53 legacy (kind=None) — basé sur category + status -----------------
    if result.kind is None:
        if result.status != "ok":
            return None
        if result.category == DispatchCategory.SSE_ONLY:
            return make_tool_invoke_event(result, message_id=message_id)
        if result.category == DispatchCategory.DB_MUTATION:
            return make_mutation_event(result, message_id=message_id)
        return None

    return None


__all__ = [
    "KNOWN_EVENTS",
    "SseEvent",
    "make_done_event",
    "make_error_event",
    "make_message_done_event",
    "make_mutation_event",
    "make_text_delta_event",
    "make_token_event",
    "make_tool_call_completed_event",
    "make_tool_call_started_event",
    "make_tool_invoke_event",
    "make_unsourced_claim_event",
    "make_validation_retry_event",
    "map_dispatch_to_sse",
]
