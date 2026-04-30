"""F35 — Post-processeur LLM : garde-fous UX (chips + bandeau non sourcé)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

_DEFAULT_PATTERNS: dict[str, list[str]] = {
    "enumeration_patterns": [
        r"(?:^|\n)\s*1[\.\)]\s+.+?(?:\n)\s*2[\.\)]\s+.+?(?:\n)\s*3[\.\)]\s+",
        r"(?:^|\n)\s*[-\*]\s+.+?(?:\n)\s*[-\*]\s+.+?(?:\n)\s*[-\*]\s+",
    ],
    "binary_choice_patterns": [
        r"pr[ée]f[ée]rez-vous\s+.+?\s+(?:ou|,)\s+.+?\?",
        r"souhaitez-vous\s+.+?\s+(?:ou|,)\s+.+?\?",
        r"(?:oui|non)\s+ou\s+(?:non|oui)\s*\?",
    ],
    "number_with_unit_patterns": [
        r"\b\d{1,3}(?:[\s \.,]?\d{3})*(?:[\.,]\d+)?\s*(?:FCFA|XOF|EUR|USD|tonnes?)\b",
        r"\b\d{1,3}(?:[\s \.,]?\d{3})*(?:[\.,]\d+)?\s*%",
        r"\b\d+\s*pourcent\b",
    ],
}

DEFAULT_PATTERNS_PATH = Path(__file__).with_name("postprocess_patterns.json")


@dataclass(frozen=True)
class PostProcessPatterns:
    """Patterns regex compilés (immuable)."""

    enumeration: tuple[re.Pattern[str], ...]
    binary_choice: tuple[re.Pattern[str], ...]
    number_with_unit: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class PostProcessSignal:
    """Signal émis par le post-processeur (immuable)."""

    type: Literal["chips_suggestion", "unsourced_warning"]
    payload: dict[str, Any] = field(default_factory=dict)


def _compile_all(patterns_dict: dict[str, list[str]]) -> PostProcessPatterns:
    def _compile(items: list[str]) -> tuple[re.Pattern[str], ...]:
        return tuple(re.compile(p, re.IGNORECASE | re.MULTILINE | re.DOTALL) for p in items)

    return PostProcessPatterns(
        enumeration=_compile(patterns_dict.get("enumeration_patterns", [])),
        binary_choice=_compile(patterns_dict.get("binary_choice_patterns", [])),
        number_with_unit=_compile(patterns_dict.get("number_with_unit_patterns", [])),
    )


@lru_cache(maxsize=4)
def load_patterns(path_str: str | None = None) -> PostProcessPatterns:
    """Charge les patterns depuis JSON (caché). Fallback sur les patterns par défaut."""
    path = Path(path_str) if path_str else DEFAULT_PATTERNS_PATH
    if not path.exists():
        return _compile_all(_DEFAULT_PATTERNS)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _compile_all(_DEFAULT_PATTERNS)
        return _compile_all(raw)
    except (OSError, json.JSONDecodeError, re.error):
        return _compile_all(_DEFAULT_PATTERNS)


def _extract_options_from_enumeration(text: str) -> list[str]:
    """Extrait les options depuis un texte d'énumération (best-effort)."""
    options: list[str] = []
    numbered = re.findall(r"(?:^|\n)\s*\d+[\.\)]\s+([^\n]+)", text)
    if numbered:
        options.extend(s.strip() for s in numbered)
    if not options:
        m = re.search(
            r"pr[ée]f[ée]rez-vous\s+(.+?)\?", text, re.IGNORECASE | re.DOTALL
        )
        if m:
            parts = re.split(r"\s*,\s*|\s+ou\s+", m.group(1))
            options.extend(p.strip() for p in parts if p.strip())
    if not options:
        m = re.search(
            r"souhaitez-vous\s+(.+?)\?", text, re.IGNORECASE | re.DOTALL
        )
        if m:
            parts = re.split(r"\s*,\s*|\s+ou\s+", m.group(1))
            options.extend(p.strip() for p in parts if p.strip())
    if not options:
        bullets = re.findall(r"(?:^|\n)\s*[-\*]\s+([^\n]+)", text)
        if bullets:
            options.extend(s.strip() for s in bullets)
    return [o for o in options if 1 <= len(o) <= 80][:6]


def _has_cite_source(tool_calls: list[dict[str, Any]]) -> bool:
    """Vrai si l'un des tool_calls est ``cite_source``."""
    for tc in tool_calls:
        name = tc.get("name") or tc.get("tool_name")
        if name == "cite_source":
            return True
    return False


def post_process(
    response_text: str | None,
    tool_calls: list[dict[str, Any]] | None = None,
    patterns: PostProcessPatterns | None = None,
) -> list[PostProcessSignal]:
    """Analyse la réponse LLM et retourne la liste des signaux émis."""
    if not response_text or not response_text.strip():
        return []
    pats = patterns if patterns is not None else load_patterns()
    tcs = tool_calls or []
    signals: list[PostProcessSignal] = []

    options: list[str] = []
    for rx in pats.enumeration:
        if rx.search(response_text):
            options = _extract_options_from_enumeration(response_text)
            break
    if not options:
        for rx in pats.binary_choice:
            if rx.search(response_text):
                options = _extract_options_from_enumeration(response_text)
                break
    if options:
        signals.append(
            PostProcessSignal(type="chips_suggestion", payload={"options": options})
        )

    if not _has_cite_source(tcs):
        for rx in pats.number_with_unit:
            m = rx.search(response_text)
            if m:
                signals.append(
                    PostProcessSignal(
                        type="unsourced_warning",
                        payload={"matched_text": m.group(0)[:200]},
                    )
                )
                break

    return signals
