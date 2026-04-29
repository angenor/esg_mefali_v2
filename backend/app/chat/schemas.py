"""F13 — Pydantic v2 schemas (extra='forbid' partout où exigé)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Limites (FR-022)
MAX_CONTENT_BYTES = 32 * 1024
MAX_PAYLOAD_JSON_BYTES = 64 * 1024


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class ContextJson(BaseModel):
    """Whitelist stricte (FR-007 / FR-025) : extra fields → 422."""

    model_config = ConfigDict(extra="forbid")

    page: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    selection: str | None = None


class ChatThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    archived: bool
    created_at: datetime
    updated_at: datetime


class ChatThreadListOut(BaseModel):
    threads: list[ChatThreadOut]


class ChatThreadCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    thread_id: UUID | None = None
    role: MessageRole
    content: str
    payload_json: dict[str, Any] | None = None
    context_json: ContextJson | None = None
    created_at: datetime


class ChatMessageListOut(BaseModel):
    messages: list[ChatMessageOut]


class PostMessageBody(BaseModel):
    """Corps d'un POST /me/chat/threads/{id}/messages."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_BYTES)
    payload_json: dict[str, Any] | None = None
    context_json: ContextJson

    @field_validator("payload_json")
    @classmethod
    def _payload_size(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        import json as _json

        if len(_json.dumps(v).encode("utf-8")) > MAX_PAYLOAD_JSON_BYTES:
            raise ValueError("payload_json too large")
        return v


# --- SSE envelopes ---
class SsEvent(BaseModel):
    """Enveloppe d'un événement SSE (assistant ou /me/events)."""

    model_config = ConfigDict(extra="forbid")
    type: Literal[
        "text_delta",
        "tool_call_started",
        "tool_call_completed",
        "message_done",
        "error",
        "entity_updated",
    ]
    data: dict[str, Any]
