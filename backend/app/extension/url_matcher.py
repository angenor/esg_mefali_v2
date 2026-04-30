"""F33 - URL pattern matcher (wildcard + regex)."""

from __future__ import annotations

import re
from typing import Final

WILDCARD_RE_CACHE: dict[str, re.Pattern[str]] = {}
REGEX_RE_CACHE: dict[str, re.Pattern[str]] = {}

VALID_TYPES: Final[frozenset[str]] = frozenset({"wildcard", "regex"})
VALID_NATURES: Final[frozenset[str]] = frozenset({"fonds", "intermediaire"})


def _wildcard_to_regex(pattern: str) -> str:
    """Convertit un pattern type ``*.boad.org/*`` en regex ancrée.

    - ``*`` matche n'importe quel caractère (sauf nouvelle ligne).
    - Les autres caractères sont echappés.
    """
    parts: list[str] = []
    for ch in pattern:
        if ch == "*":
            parts.append(".*")
        else:
            parts.append(re.escape(ch))
    return "^" + "".join(parts) + "$"


def compile_pattern(pattern: str, pattern_type: str) -> re.Pattern[str]:
    """Compile et cache un pattern. Lève ValueError si invalide."""
    if pattern_type not in VALID_TYPES:
        raise ValueError(f"pattern_type invalide: {pattern_type}")
    if not pattern or not isinstance(pattern, str):
        raise ValueError("pattern vide")
    if pattern_type == "wildcard":
        cached = WILDCARD_RE_CACHE.get(pattern)
        if cached is None:
            cached = re.compile(_wildcard_to_regex(pattern), re.IGNORECASE)
            WILDCARD_RE_CACHE[pattern] = cached
        return cached
    cached = REGEX_RE_CACHE.get(pattern)
    if cached is None:
        try:
            cached = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:  # pragma: no cover - validated upstream
            raise ValueError(f"regex invalide: {exc}") from exc
        REGEX_RE_CACHE[pattern] = cached
    return cached


def match_url(url: str, pattern: str, pattern_type: str) -> bool:
    """Retourne True si ``url`` matche ``pattern`` selon ``pattern_type``."""
    if not url:
        return False
    try:
        compiled = compile_pattern(pattern, pattern_type)
    except ValueError:
        return False
    return compiled.match(url) is not None
