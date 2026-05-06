"""F54 / FR-005 — count_tokens(text, encoding) avec tiktoken + fallback.

tiktoken (encoding ``cl100k_base`` par défaut) donne une approximation
correcte pour les modèles compatibles GPT-4 / OpenRouter. Pour les modèles
non OpenAI (minimax-m2.7, ...), tiktoken sous-estime de ~5–10 % — la marge
est absorbée par :data:`Settings.LLM_AGENT_PROMPT_BUDGET_TOKENS` (4000).

Si l'encoding demandé n'est pas reconnu (typiquement un encoding inconnu de
tiktoken), on utilise un fallback heuristique ``len(text) // 4`` qui est
**plus pessimiste** (sous-estime moins) : on préfère couper trop que pas
assez.

Cf. :doc:`specs/054-agent-context-builder/research.md` (R1).
"""

from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

#: Fallback ratio caractères → tokens (latin script ~4 chars = 1 token).
_FALLBACK_CHARS_PER_TOKEN: int = 4


@lru_cache(maxsize=8)
def _get_encoding(name: str):  # type: ignore[no-untyped-def]
    """Récupère un objet tiktoken Encoding ; lève si absent (catché en amont)."""
    import tiktoken

    return tiktoken.get_encoding(name)


def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    """Compte les tokens du ``text`` selon ``encoding`` tiktoken.

    Si ``encoding`` est inconnu ou si tiktoken n'est pas importable, on bascule
    sur un fallback heuristique ``len(text) // 4`` — toujours ``>= 1`` pour
    un texte non vide.
    """
    if not text:
        return 0

    if not encoding:
        return _fallback_count(text)

    try:
        enc = _get_encoding(encoding)
        return len(enc.encode(text, disallowed_special=()))
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "count_tokens: tiktoken failed for encoding %r (%s) — fallback len/4",
            encoding,
            exc,
        )
        return _fallback_count(text)


def _fallback_count(text: str) -> int:
    n = len(text) // _FALLBACK_CHARS_PER_TOKEN
    return max(1, n) if text else 0


__all__ = ["count_tokens"]
