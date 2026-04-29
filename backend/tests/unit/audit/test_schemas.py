"""F04 — Unit tests for audit Pydantic schemas (T023)."""

from __future__ import annotations

from datetime import UTC
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.audit.schemas import (
    AuditLogEntryIn,
    AuditLogEntryOut,
    AuditLogPage,
    SourceOfChange,
)


def test_source_of_change_enum_closed() -> None:
    assert {e.value for e in SourceOfChange} == {
        "manual",
        "llm",
        "import",
        "admin",
        "system",
    }


def test_audit_in_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        AuditLogEntryIn(
            entity_type="x",
            entity_id=uuid4(),
            unknown_field="boom",
        )


def test_audit_in_minimal() -> None:
    eid = uuid4()
    a = AuditLogEntryIn(entity_type="projet", entity_id=eid)
    assert a.source_of_change == SourceOfChange.MANUAL
    assert a.entity_id == eid


def test_audit_page_clamp_bounds() -> None:
    p = AuditLogPage(items=[], total=0, page=1, page_size=10)
    assert p.page_size == 10
    with pytest.raises(ValidationError):
        AuditLogPage(items=[], total=0, page=0, page_size=10)
    with pytest.raises(ValidationError):
        AuditLogPage(items=[], total=0, page=1, page_size=999)


def test_audit_out_extra_forbid() -> None:
    from datetime import datetime

    with pytest.raises(ValidationError):
        AuditLogEntryOut(
            id=uuid4(),
            timestamp=datetime.now(tz=UTC),
            entity_type="x",
            entity_id=uuid4(),
            source_of_change=SourceOfChange.MANUAL,
            extra_garbage=1,
        )
