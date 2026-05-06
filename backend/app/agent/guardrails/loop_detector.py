"""F58 — Détection de boucles d'agent (FR-016).

Trois cas couverts :
- (a) ``len(history) + 1 > max_per_turn`` → forcer ``compose_response``.
- (b) Même tool + même hash(args) répété ``max_consecutive_identical`` fois
  consécutives → boucle, agent stoppe.
- (c) > 5 tours sans interaction utilisateur → assertion défensive
  (vérifié au niveau du runner avec ``reinvoke_count``).

Hash des args : ``sha256(json.dumps(sort_keys=True, default=str))`` —
déterministe, gère UUID / datetime via ``default=str``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

LoopReason = Literal["none", "too_many_calls", "identical_args_3x"]


@dataclass(frozen=True)
class LoopDetectionResult:
    """Résultat retourné par :func:`detect_loop`. Immutable."""

    triggered: bool
    reason: LoopReason
    last_tool_name: str | None
    last_args_hash: str | None


def args_hash(args: Mapping[str, Any]) -> str:
    """SHA256(json.dumps(args, sort_keys=True, default=str)).

    Hexa lower-case, 64 chars. Déterministe (sort_keys), gère UUID et
    datetime via ``default=str``.
    """
    payload = json.dumps(dict(args), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_call(call: Mapping[str, Any] | Any) -> tuple[str, dict]:
    """Tolérant : accepte dict ``{name, arguments|args}`` ou objet ``ToolCall``."""
    if isinstance(call, Mapping):
        name = str(call.get("name") or "")
        args = call.get("arguments")
        if args is None:
            args = call.get("args")
        if not isinstance(args, Mapping):
            args = {}
        return name, dict(args)
    name = str(getattr(call, "name", "") or "")
    args = getattr(call, "arguments", None)
    if args is None:
        args = getattr(call, "args", None)
    if not isinstance(args, Mapping):
        args = {}
    return name, dict(args)


def detect_loop(
    history: Sequence[Mapping[str, Any] | Any],
    new_call: Mapping[str, Any] | Any,
    *,
    max_consecutive_identical: int = 3,
    max_per_turn: int = 10,
) -> LoopDetectionResult:
    """Détecte une boucle d'agent à l'arrivée d'un nouveau ``new_call``.

    Args:
        history: liste des tool calls déjà émis dans le tour.
        new_call: tool call envisagé.
        max_consecutive_identical: seuil identique-args (défaut 3).
        max_per_turn: cap absolu d'appels par tour (défaut 10).
    """
    new_name, new_args = _normalize_call(new_call)
    new_hash = args_hash(new_args)

    # (a) too many calls per turn
    if len(history) + 1 > max_per_turn:
        return LoopDetectionResult(
            triggered=True,
            reason="too_many_calls",
            last_tool_name=new_name,
            last_args_hash=new_hash,
        )

    # (b) Même tool + même args répétés N fois consécutives
    # On compte combien d'appels consécutifs en fin d'historique correspondent
    # exactement au new_call.
    consecutive = 1  # le new_call lui-même
    for prev in reversed(history):
        prev_name, prev_args = _normalize_call(prev)
        if prev_name != new_name:
            break
        if args_hash(prev_args) != new_hash:
            break
        consecutive += 1
    if consecutive >= max_consecutive_identical:
        return LoopDetectionResult(
            triggered=True,
            reason="identical_args_3x",
            last_tool_name=new_name,
            last_args_hash=new_hash,
        )

    return LoopDetectionResult(
        triggered=False,
        reason="none",
        last_tool_name=new_name,
        last_args_hash=new_hash,
    )


__all__ = [
    "LoopDetectionResult",
    "LoopReason",
    "args_hash",
    "detect_loop",
]
