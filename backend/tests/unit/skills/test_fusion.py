"""Tests F19 — fusion prompt."""

from __future__ import annotations

import uuid

from app.skills.fusion import (
    SKILL_PROMPT_MAX_TOKENS,
    build_prompt,
    estimate_tokens,
    is_within_budget,
)
from app.skills.sources import ResolvedSource


def _src(idx: int) -> ResolvedSource:
    return ResolvedSource(
        id=uuid.uuid4(),
        title=f"Titre {idx}",
        publisher=f"Éditeur {idx}",
        url=f"https://example.com/{idx}",
        excerpt=f"Extrait court source {idx}.",
    )


def test_estimate_tokens() -> None:
    assert estimate_tokens("a" * 4) == 1
    assert estimate_tokens("a" * 400) == 100


def test_build_prompt_contains_all_sections() -> None:
    prompt = build_prompt(
        global_invariants="Sourçage obligatoire.",
        skill_name="skill_esg_diagnostic",
        skill_prompt_expert="Tu es expert ESG.",
        procedure="1. Lire le profil.\n2. Calculer.",
        sources_resolved=[_src(1), _src(2)],
        context={"page": "/profil/projets/x", "intent": "analyse"},
        tools=["update_demo_profile", "ask_qcu"],
    )
    for header in (
        "## Invariants",
        "## Skill: skill_esg_diagnostic",
        "## Sources de référence",
        "## Procédure",
        "## Tools disponibles",
        "## Contexte",
    ):
        assert header in prompt
    assert "Tu es expert ESG." in prompt
    assert "ask_qcu" in prompt


def test_build_prompt_handles_empty_sources_and_tools() -> None:
    prompt = build_prompt(
        global_invariants="X",
        skill_name="s",
        skill_prompt_expert="p",
        procedure="",
        sources_resolved=[],
        context={},
        tools=[],
    )
    assert "_(aucune source pré-résolue)_" in prompt
    assert "_(aucun)_" in prompt


def test_within_budget() -> None:
    short = "ok" * 100
    assert is_within_budget(short)
    long_text = "a" * (SKILL_PROMPT_MAX_TOKENS * 4 + 100)
    assert is_within_budget(long_text) is False
