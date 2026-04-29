"""Tests F16 — _viz_common (mixins partagés)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.orchestrator.tools._viz_common import (
    AltTextMixin,
    SourceRequiredMixin,
    ensure_internal_link,
)


def test_alt_text_required() -> None:
    with pytest.raises(ValidationError):
        AltTextMixin(alt_text="")


def test_alt_text_max_length() -> None:
    with pytest.raises(ValidationError):
        AltTextMixin(alt_text="x" * 513)


def test_alt_text_ok() -> None:
    m = AltTextMixin(alt_text="Description")
    assert m.alt_text == "Description"


def test_source_ids_required_non_empty() -> None:
    with pytest.raises(ValidationError):
        SourceRequiredMixin(source_ids=[])


def test_source_ids_max_length() -> None:
    with pytest.raises(ValidationError):
        SourceRequiredMixin(source_ids=list(range(21)))


def test_source_ids_ok() -> None:
    m = SourceRequiredMixin(source_ids=[1, 2, 3])
    assert m.source_ids == [1, 2, 3]


def test_internal_link_ok() -> None:
    assert ensure_internal_link("/foo/bar?x=1") == "/foo/bar?x=1"


def test_external_link_rejected() -> None:
    with pytest.raises(ValueError):
        ensure_internal_link("https://evil.example.com")


def test_protocol_relative_link_rejected() -> None:
    with pytest.raises(ValueError):
        ensure_internal_link("//evil.example.com")


def test_empty_link_rejected() -> None:
    with pytest.raises(ValueError):
        ensure_internal_link("")
