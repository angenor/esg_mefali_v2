"""Tests pour `app.core.pseudonymize` (F05 — T006 support)."""

from __future__ import annotations

from uuid import UUID

import pytest

from app.config import get_settings
from app.core.pseudonymize import PseudonymPepperMissingError, pseudonymize


@pytest.fixture
def _set_pepper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        get_settings(),
        "PURGE_PSEUDONYM_PEPPER",
        "a" * 64,
        raising=False,
    )


def test_pseudonymize_deterministic(_set_pepper: None) -> None:
    uid = UUID("00000000-0000-0000-0000-000000000001")
    a = pseudonymize(uid)
    b = pseudonymize(uid)
    assert a == b
    assert a.startswith("anon_")
    assert len(a) == len("anon_") + 16


def test_pseudonymize_different_inputs_differ(_set_pepper: None) -> None:
    a = pseudonymize(UUID("00000000-0000-0000-0000-000000000001"))
    b = pseudonymize(UUID("00000000-0000-0000-0000-000000000002"))
    assert a != b


def test_pseudonymize_missing_pepper_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "PURGE_PSEUDONYM_PEPPER", "", raising=False)
    with pytest.raises(PseudonymPepperMissingError):
        pseudonymize(UUID("00000000-0000-0000-0000-000000000003"))


def test_pseudonymize_invalid_pepper_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "PURGE_PSEUDONYM_PEPPER", "zzz", raising=False)
    with pytest.raises(PseudonymPepperMissingError):
        pseudonymize(UUID("00000000-0000-0000-0000-000000000004"))
