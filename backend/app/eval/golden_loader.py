"""F35 — Loader du golden set d'évaluation LLM.

Charge des cas depuis un fichier JSON (10–20 cas seed). Format :

    {
        "id": "qcu-forme-juridique",
        "description": "...",
        "context": {"page": "...", "intent": "...", "entity": null},
        "user_message": "...",
        "expected": {"tool": "...", "payload_partial": {...}},
        "tags": ["..."]
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GoldenContext:
    """Contexte d'un cas (page + intent + entity)."""

    page: str | None = None
    intent: str | None = None
    entity: str | None = None


@dataclass(frozen=True)
class GoldenExpected:
    """Attendu d'un cas (tool name + contraintes payload)."""

    tool: str
    payload_partial: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoldenCase:
    """Un cas du golden set (immuable)."""

    id: str
    description: str
    context: GoldenContext
    user_message: str
    expected: GoldenExpected
    tags: tuple[str, ...] = ()


def _parse_case(raw: dict[str, Any]) -> GoldenCase:
    """Parse un dict brut en ``GoldenCase``. Lève ``ValueError`` si malformé."""
    for required in ("id", "description", "user_message", "expected"):
        if required not in raw:
            raise ValueError(f"golden case malformed: missing '{required}'")

    expected_raw = raw["expected"]
    if not isinstance(expected_raw, dict) or "tool" not in expected_raw:
        raise ValueError(f"golden case '{raw.get('id')}': expected.tool missing")

    ctx_raw = raw.get("context") or {}
    if not isinstance(ctx_raw, dict):
        raise ValueError(f"golden case '{raw['id']}': context must be an object")

    tags_raw = raw.get("tags") or []
    if not isinstance(tags_raw, list) or not all(isinstance(t, str) for t in tags_raw):
        raise ValueError(f"golden case '{raw['id']}': tags must be a list of strings")

    return GoldenCase(
        id=str(raw["id"]),
        description=str(raw["description"]),
        context=GoldenContext(
            page=ctx_raw.get("page"),
            intent=ctx_raw.get("intent"),
            entity=ctx_raw.get("entity"),
        ),
        user_message=str(raw["user_message"]),
        expected=GoldenExpected(
            tool=str(expected_raw["tool"]),
            payload_partial=dict(expected_raw.get("payload_partial") or {}),
        ),
        tags=tuple(tags_raw),
    )


def load_cases(
    path: Path,
    *,
    filter_tags: list[str] | None = None,
) -> list[GoldenCase]:
    """Charge le golden set depuis ``path`` (JSON)."""
    if not path.exists():
        raise FileNotFoundError(f"golden set not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"golden set: invalid JSON ({exc})") from exc
    if not isinstance(raw, list):
        raise ValueError("golden set: top-level must be a list of cases")

    cases = [_parse_case(item) for item in raw]
    if filter_tags:
        wanted = set(filter_tags)
        cases = [c for c in cases if wanted.intersection(c.tags)]
    return cases
