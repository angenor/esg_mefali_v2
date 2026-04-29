"""F10 T016 — unit tests for ``mask_pii``."""

from __future__ import annotations

from app.admin.services.pii_filter import MASK, mask_pii


def test_mask_email() -> None:
    assert MASK in mask_pii("contact: john.doe@example.com please")  # type: ignore[operator]


def test_mask_phone() -> None:
    assert MASK in mask_pii("call +212 6 12 34 56 78 today")  # type: ignore[operator]


def test_mask_iban() -> None:
    assert MASK in mask_pii("Send to FR7630006000011234567890189 now")  # type: ignore[operator]


def test_mask_cin() -> None:
    assert MASK in mask_pii("CIN: AB123456 verified")  # type: ignore[operator]


def test_passthrough_none() -> None:
    assert mask_pii(None) is None


def test_clean_text_unchanged() -> None:
    assert mask_pii("hello world") == "hello world"
