"""F55 — Sérialisation des résultats READ tronqués (FR-015, US5).

Convertit le résultat d'un handler READ en JSON structuré tronqué à un
budget de tokens (heuristique 4 chars/token). Évite l'inflation du contexte
LLM et la sur-facturation.
"""

from __future__ import annotations

import json
from typing import Any

# Heuristique simple : 1 token ≈ 4 caractères en latin
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Heuristique de comptage de tokens (sans tiktoken pour rester léger)."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _truncate_string(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max(0, max_chars - 3)] + "..."


def _truncate_obj(obj: Any, *, char_budget: int) -> Any:
    """Truncate récursif au budget. Best-effort, focused sur lisibilité."""
    if isinstance(obj, str):
        return _truncate_string(obj, char_budget)
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        remaining = char_budget
        for k, v in obj.items():
            if remaining <= 0:
                out["_truncated"] = True
                break
            sub_budget = max(8, remaining // max(1, len(obj)))
            out[k] = _truncate_obj(v, char_budget=sub_budget)
            remaining -= len(json.dumps(out[k], default=str))
        return out
    if isinstance(obj, list):
        out_list: list[Any] = []
        remaining = char_budget
        for item in obj:
            if remaining <= 0:
                out_list.append({"_truncated": True})
                break
            sub_budget = max(8, remaining // max(1, len(obj)))
            sub = _truncate_obj(item, char_budget=sub_budget)
            out_list.append(sub)
            remaining -= len(json.dumps(sub, default=str))
        return out_list
    return obj


def serialize_read_result(payload: Any, *, budget_tokens: int = 1500) -> str:
    """Sérialise le résultat d'un READ en JSON tronqué.

    - ``payload`` peut être dict, list ou objet sérialisable.
    - ``budget_tokens`` : budget total souhaité (heuristique 4 chars/token).

    Retour : string JSON ; ne dépasse pas ``budget_tokens * 4`` chars (best
    effort, +/- 5 % au plus).
    """
    char_budget = max(64, budget_tokens * CHARS_PER_TOKEN)
    truncated = _truncate_obj(payload, char_budget=char_budget)
    serialized = json.dumps(truncated, ensure_ascii=False, default=str)
    if len(serialized) > char_budget:
        serialized = serialized[: char_budget - 3] + "..."
    return serialized


__all__ = ["estimate_tokens", "serialize_read_result"]
