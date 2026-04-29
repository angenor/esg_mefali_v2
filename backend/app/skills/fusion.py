"""F19 — Fusion prompt système + skill prompt + sources + procédure + tools.

Sortie en markdown structuré, sections fixes pour faciliter le parsing humain
et la stabilité face au LLM. Estimation tokens approximée (chars/4) cohérente
avec F18.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.skills.sources import ResolvedSource

SKILL_PROMPT_MAX_TOKENS = 1500  # FR-008
CHARS_PER_TOKEN = 4  # Approximation cohérente F18


def estimate_tokens(text: str) -> int:
    """Approximation tokens = nb caractères / 4."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _format_sources(sources: Iterable[ResolvedSource]) -> str:
    items = list(sources)
    if not items:
        return "_(aucune source pré-résolue)_"
    lines = []
    for i, src in enumerate(items, start=1):
        lines.append(
            f"[{i}] **{src.title}** — {src.publisher}  \n"
            f"    URL: {src.url}  \n"
            f"    ID: `{src.id}`  \n"
            f"    Extrait: {src.excerpt}"
        )
    return "\n\n".join(lines)


def _format_tools(tools: Iterable[str]) -> str:
    items = list(tools)
    if not items:
        return "_(aucun)_"
    return "\n".join(f"- `{t}`" for t in items)


def _format_context(context: dict[str, Any]) -> str:
    if not context:
        return "_(aucun)_"
    lines = []
    for key, value in context.items():
        lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)


def build_prompt(
    *,
    global_invariants: str,
    skill_name: str,
    skill_prompt_expert: str,
    procedure: str,
    sources_resolved: Iterable[ResolvedSource],
    context: dict[str, Any],
    tools: Iterable[str],
) -> str:
    """Construit le prompt système final injecté au LLM (FR-005).

    Sections :
    - ## Invariants
    - ## Skill: <name>
    - ## Sources de référence
    - ## Procédure
    - ## Tools disponibles
    - ## Contexte
    """
    sections = [
        "## Invariants",
        global_invariants.strip() or "_(aucun)_",
        "",
        f"## Skill: {skill_name}",
        skill_prompt_expert.strip(),
        "",
        "## Sources de référence",
        _format_sources(sources_resolved),
        "",
        "## Procédure",
        procedure.strip() or "_(aucune procédure définie)_",
        "",
        "## Tools disponibles",
        _format_tools(tools),
        "",
        "## Contexte",
        _format_context(context),
    ]
    return "\n".join(sections)


def is_within_budget(prompt: str, *, max_tokens: int = SKILL_PROMPT_MAX_TOKENS) -> bool:
    """True si le prompt rentre dans le budget (chars/4 ≤ max_tokens)."""
    return estimate_tokens(prompt) <= max_tokens


__all__ = [
    "CHARS_PER_TOKEN",
    "SKILL_PROMPT_MAX_TOKENS",
    "build_prompt",
    "estimate_tokens",
    "is_within_budget",
]
