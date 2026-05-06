"""F56 / T031 — Tests unit pour ``normalize_claim``."""

from __future__ import annotations

import pytest

from app.agent.sourcing.normalizer import normalize_claim


@pytest.mark.unit
def test_empty_returns_empty():
    assert normalize_claim("") == ""
    assert normalize_claim(None) == ""  # type: ignore[arg-type]


@pytest.mark.unit
def test_lowercase():
    assert normalize_claim("ABC") == "abc"


@pytest.mark.unit
def test_strips_punctuation():
    assert normalize_claim("Le Seuil, GCF !") == "le seuil gcf"


@pytest.mark.unit
def test_collapses_whitespace():
    assert normalize_claim("  Le   seuil    GCF  ") == "le seuil gcf"


@pytest.mark.unit
def test_idempotent():
    raw = "Le seuil GCF, 50 M USD."
    norm = normalize_claim(raw)
    assert normalize_claim(norm) == norm


@pytest.mark.unit
def test_preserves_unicode_letters():
    assert "é" in normalize_claim("Réduction de 15%")
