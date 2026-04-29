"""Classifier d'intention rule-based + cache TTL (US2).

MVP : règles déterministes uniquement. Le fallback LLM est différé
(``[DEFERRED]`` dans tasks.md). Cache TTL maison sur ``thread_id``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.orchestrator.schemas import Intent

CACHE_TTL_SECONDS = 600  # 10 minutes glissant (clarification spec)

# Règles déterministes minimales : mots-clés FR → intention.
# Ordre important : la première règle qui matche gagne.
_RULES: tuple[tuple[tuple[str, ...], Intent], ...] = (
    (("ajoute", "crée", "supprime", "modifie", "mets à jour", "change"), "mutation"),
    (("compare", "analyse", "explique pourquoi", "performance"), "analyse"),
    (("aide", "comment", "que fais-tu", "que peux-tu"), "aide"),
    (("oui", "non", "confirmer", "confirme"), "question_fermee"),
    (("va à", "ouvre la page", "navigue", "retour"), "navigation"),
    (("mon profil", "mon entreprise", "mes infos"), "profilage"),
)


@dataclass(frozen=True)
class _CacheEntry:
    intent: Intent
    expires_at: float


_CACHE: dict[str, _CacheEntry] = {}


def _from_cache(thread_id: str | None) -> Intent | None:
    if thread_id is None:
        return None
    entry = _CACHE.get(thread_id)
    if entry is None:
        return None
    if entry.expires_at < time.monotonic():
        _CACHE.pop(thread_id, None)
        return None
    return entry.intent


def _to_cache(thread_id: str | None, intent: Intent) -> None:
    if thread_id is None:
        return
    _CACHE[thread_id] = _CacheEntry(
        intent=intent, expires_at=time.monotonic() + CACHE_TTL_SECONDS
    )


def classify(message: str, thread_id: str | None = None) -> Intent:
    """Classifie ``message`` en une ``Intent``.

    MVP : règles seulement. Si aucune règle ne matche → ``autre``.
    """
    cached = _from_cache(thread_id)

    lowered = message.lower()
    for keywords, intent in _RULES:
        if any(kw in lowered for kw in keywords):
            _to_cache(thread_id, intent)
            return intent

    if cached is not None:
        return cached

    _to_cache(thread_id, "autre")
    return "autre"


def clear_cache() -> None:
    """Vide le cache (réservé aux tests)."""
    _CACHE.clear()


__all__ = ["classify", "clear_cache", "CACHE_TTL_SECONDS"]
