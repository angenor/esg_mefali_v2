"""F56 — Normalisation de claim pour la dédup.

La clé de dédup ``unsourced_flag(account_id, thread_id, lower(claim))``
(Q1 clarification) impose une normalisation côté SQL via ``lower(...)``.
Côté application, on fournit ``normalize_claim`` pour la même intention :
collapse whitespace + lowercase + strip ponctuation.
"""

from __future__ import annotations

import re

_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_claim(text: str) -> str:
    """Normalise un claim pour la comparaison de dédup.

    Étapes :
    1. ``strip`` extérieur,
    2. ``lower``,
    3. supprime la ponctuation,
    4. collapse les espaces.
    """
    if not text:
        return ""
    t = text.strip().lower()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


__all__ = ["normalize_claim"]
