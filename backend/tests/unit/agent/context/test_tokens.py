"""F54 / T014 — Tests unitaires count_tokens (FR-005).

Couvre :
- Comptage tiktoken sur encoding ``cl100k_base``.
- Fallback heuristique ``len/4`` sur encoding inconnu.
- Texte vide → 0.
- Cohérence FR/EN (pas de plantage sur accents).
"""

from __future__ import annotations

import pytest

from app.agent.context.tokens import count_tokens


@pytest.mark.unit
class TestCountTokens:
    def test_empty_string_is_zero(self) -> None:
        assert count_tokens("") == 0

    def test_simple_english(self) -> None:
        # ``hello world`` → 2 tokens en cl100k_base.
        n = count_tokens("hello world")
        assert n >= 1
        assert n < 10  # généreux, mais évite les régressions énormes.

    def test_simple_french_with_accents(self) -> None:
        # Le tokenizer doit gérer les accents sans planter.
        n = count_tokens("Bonjour, ESG Mefali — finance verte ouest-africaine !")
        assert n > 0
        assert n < 50

    def test_unknown_encoding_uses_fallback(self) -> None:
        text = "a" * 80
        n = count_tokens(text, encoding="not-a-real-encoding-xyz")
        # Fallback heuristique : len/4 → 20 (conservateur).
        assert n == 20

    def test_fallback_handles_short_text(self) -> None:
        # 3 chars, len/4 = 0.75 → ceil ou floor : implémentation = max(1, len//4).
        n = count_tokens("abc", encoding="not-a-real-encoding")
        assert n >= 1

    def test_default_encoding_is_cl100k_base(self) -> None:
        # Sans paramètre, on utilise cl100k_base.
        n_default = count_tokens("hello world")
        n_explicit = count_tokens("hello world", encoding="cl100k_base")
        assert n_default == n_explicit

    def test_long_text_is_proportional(self) -> None:
        short = count_tokens("hello world")
        long = count_tokens("hello world " * 100)
        assert long > short * 50  # ~100x plus de tokens.

    def test_fallback_function_is_robust_to_invalid_encoding(self) -> None:
        # Aucune exception levée même sur encoding farfelu.
        assert count_tokens("test", encoding="") >= 1
