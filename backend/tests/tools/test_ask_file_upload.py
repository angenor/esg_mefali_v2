"""Tests F15 — ask_file_upload."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.ask_file_upload import AskFileUploadPayload, register


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "question": "Uploader le BP ?",
        "attach_to": {"entity_type": "projet"},
        "accepted_mime": ["application/pdf"],
        "max_size_mb": 10,
    }
    base.update(overrides)
    return base


def test_register_adds_tool() -> None:
    register()
    assert "ask_file_upload" in TOOL_REGISTRY


def test_basic_payload() -> None:
    p = AskFileUploadPayload(**_payload())
    assert p.attach_to.entity_type == "projet"
    assert p.attach_to.entity_id is None


def test_with_entity_id() -> None:
    eid = uuid4()
    p = AskFileUploadPayload(
        **_payload(attach_to={"entity_type": "entreprise", "entity_id": str(eid)})
    )
    assert p.attach_to.entity_id == eid


def test_invalid_entity_type_rejected() -> None:
    with pytest.raises(ValidationError):
        AskFileUploadPayload(**_payload(attach_to={"entity_type": "candidature"}))


def test_empty_mime_list_rejected() -> None:
    with pytest.raises(ValidationError):
        AskFileUploadPayload(**_payload(accepted_mime=[]))


def test_invalid_mime_format_rejected() -> None:
    with pytest.raises(ValidationError):
        AskFileUploadPayload(**_payload(accepted_mime=["pdf"]))


def test_max_size_too_low_rejected() -> None:
    with pytest.raises(ValidationError):
        AskFileUploadPayload(**_payload(max_size_mb=0))


def test_max_size_too_high_rejected() -> None:
    with pytest.raises(ValidationError):
        AskFileUploadPayload(**_payload(max_size_mb=200))


def test_html_in_question_rejected() -> None:
    with pytest.raises(ValidationError):
        AskFileUploadPayload(**_payload(question="<x>"))


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        AskFileUploadPayload(**_payload(rogue=1))
