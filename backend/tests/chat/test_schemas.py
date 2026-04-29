"""F13 — Tests unitaires schémas Pydantic (whitelist context_json, body limits)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.chat.schemas import MAX_PAYLOAD_JSON_BYTES, ContextJson, PostMessageBody


def test_context_json_extra_field_forbidden():
    with pytest.raises(ValidationError):
        ContextJson(page="/", entity_type=None, entity_id=None, selection=None, secret="x")  # type: ignore[call-arg]


def test_post_message_body_extra_forbidden():
    with pytest.raises(ValidationError):
        PostMessageBody(content="x", context_json={"page": "/"}, foo=1)  # type: ignore[call-arg]


def test_post_message_body_oversized_content():
    with pytest.raises(ValidationError):
        PostMessageBody(content="x" * (33 * 1024), context_json={"page": "/"})


def test_post_message_body_oversized_payload_json():
    big_payload = {"k": "x" * (MAX_PAYLOAD_JSON_BYTES + 100)}
    with pytest.raises(ValidationError):
        PostMessageBody(content="ok", payload_json=big_payload, context_json={"page": "/"})


def test_post_message_body_minimal_ok():
    body = PostMessageBody(content="hi", context_json={"page": "/"})
    assert body.content == "hi"
    assert body.context_json.page == "/"
