"""Politique de retry du pipeline F14 (US7).

Règle : max 2 retries sur erreur de validation, puis fallback texte.
"""

from __future__ import annotations

from typing import Literal

from app.orchestrator.payload_validator import format_for_llm
from app.orchestrator.schemas import ValidationErrorDetail

MAX_RETRIES = 2

FALLBACK_TEXT = (
    "Je n'ai pas pu produire une action exécutable fiable. "
    "Pouvez-vous reformuler votre demande ou préciser les valeurs attendues ?"
)

Decision = Literal["retry", "fallback"]


def decide(retry_count: int) -> Decision:
    """Décide de retenter ou de basculer sur le fallback texte.

    ``retry_count`` est le nombre de retries DÉJÀ effectués.
    """
    if retry_count < MAX_RETRIES:
        return "retry"
    return "fallback"


def build_retry_prompt(errors: list[ValidationErrorDetail], retry_count: int) -> str:
    """Construit le message court envoyé au LLM pour la tentative suivante."""
    return (
        f"Tentative {retry_count + 1}/{MAX_RETRIES + 1} : ton précédent payload "
        f"ne respecte pas le schéma.\n{format_for_llm(errors)}\n"
        "Réémets uniquement le payload corrigé en JSON strict, "
        "sans champ supplémentaire."
    )


__all__ = ["MAX_RETRIES", "FALLBACK_TEXT", "decide", "build_retry_prompt"]
