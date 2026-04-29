"""Sélecteur de tools borné à 5–10 (US3)."""

from __future__ import annotations

from app.orchestrator.schemas import Intent
from app.orchestrator.tool_registry import TOOL_REGISTRY

MAX_TOOLS = 10
DEFAULT_TOOLS: tuple[str, ...] = ("ask_qcu", "ask_yes_no")

_BY_INTENT: dict[Intent, tuple[str, ...]] = {
    "mutation": ("update_demo_profile", "ask_qcu", "ask_yes_no"),
    "analyse": ("show_summary_card", "search_demo_source"),
    "aide": ("ask_qcu", "ask_yes_no"),
    "question_fermee": ("ask_yes_no", "ask_qcu"),
    "navigation": ("show_summary_card",),
    "profilage": ("update_demo_profile", "ask_qcu"),
    "autre": ("ask_qcu", "ask_yes_no"),
}


def select(
    intent: Intent,
    *,
    page: str | None = None,
    skill_whitelist: tuple[str, ...] | None = None,
) -> list[str]:
    """Retourne au maximum ``MAX_TOOLS`` tools, jamais vide si registre non-vide.

    - Filtre les candidats au registre actuel.
    - Intersecte avec ``skill_whitelist`` si fourni (FR-017).
    - Renvoie ``DEFAULT_TOOLS`` (filtrés) si la sélection est vide.
    """
    candidates = list(_BY_INTENT.get(intent, DEFAULT_TOOLS))
    candidates = [t for t in candidates if t in TOOL_REGISTRY]

    if skill_whitelist is not None:
        whitelist_set = set(skill_whitelist)
        candidates = [t for t in candidates if t in whitelist_set]

    if not candidates:
        candidates = [t for t in DEFAULT_TOOLS if t in TOOL_REGISTRY]
        if not candidates:
            candidates = list(TOOL_REGISTRY.keys())

    return candidates[:MAX_TOOLS]


__all__ = ["select", "MAX_TOOLS", "DEFAULT_TOOLS"]
