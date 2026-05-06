"""F54 — Tests unitaires hashing (FR-015)."""

from __future__ import annotations

import pytest

from app.agent.context.hashing import compute_prompt_hash


@pytest.mark.unit
class TestComputePromptHash:
    def test_hex_64_chars(self) -> None:
        h = compute_prompt_hash("hello")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self) -> None:
        a = compute_prompt_hash("Tu es ESG Mefali...")
        b = compute_prompt_hash("Tu es ESG Mefali...")
        assert a == b

    def test_different_input_different_hash(self) -> None:
        a = compute_prompt_hash("a")
        b = compute_prompt_hash("b")
        assert a != b

    def test_empty_string(self) -> None:
        h = compute_prompt_hash("")
        # SHA-256("") = e3b0c44... (constante connue).
        assert h == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_utf8_encoding(self) -> None:
        a = compute_prompt_hash("Café")
        b = compute_prompt_hash("Café")
        assert a == b
        assert len(a) == 64
