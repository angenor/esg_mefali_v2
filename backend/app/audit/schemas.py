"""F04 — Pydantic v2 schemas for the audit log."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceOfChange(StrEnum):
    """Closed enum for the ``source_of_change`` column.

    Mirrors the Postgres ``source_of_change_t`` ENUM.
    """

    MANUAL = "manual"
    LLM = "llm"
    IMPORT = "import"
    ADMIN = "admin"
    SYSTEM = "system"


class AuditLogEntryIn(BaseModel):
    """Input model accepted by :func:`record_audit`."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str
    entity_id: UUID
    field: str | None = None
    old_value: Any = None
    new_value: Any = None
    source_of_change: SourceOfChange = SourceOfChange.MANUAL
    notes: str | None = None


class AuditLogEntryOut(BaseModel):
    """Output model returned by the read endpoint."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID | None = None
    account_id: UUID | None = None
    timestamp: datetime
    entity_type: str
    entity_id: UUID
    field: str | None = None
    old_value: Any = None
    new_value: Any = None
    source_of_change: SourceOfChange
    request_id: str | None = None
    ip: str | None = None


class AuditLogPage(BaseModel):
    """Paginated response envelope (per common/patterns.md)."""

    model_config = ConfigDict(extra="forbid")

    items: list[AuditLogEntryOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
