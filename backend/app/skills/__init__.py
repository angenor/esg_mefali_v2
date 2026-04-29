"""F19 — Moteur de Skills (loader, fusion prompt, sources, snapshot, priorité)."""

from app.skills.activation_rules import ActivationRules, Match, matches_context
from app.skills.fusion import build_prompt
from app.skills.loader import load_active_skills
from app.skills.priority import compare_skills, domain_priority
from app.skills.snapshot import snapshot_skill_version
from app.skills.sources import ResolvedSource, resolve_sources

__all__ = [
    "ActivationRules",
    "Match",
    "ResolvedSource",
    "build_prompt",
    "compare_skills",
    "domain_priority",
    "load_active_skills",
    "matches_context",
    "resolve_sources",
    "snapshot_skill_version",
]
