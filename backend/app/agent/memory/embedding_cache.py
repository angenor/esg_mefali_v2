"""F57 — Cache embedding par tour (US8 / FR-011).

Le cache est attaché au ``AgentState.embedding_cache`` en champ transient
(``exclude=True``) — cycle de vie = un cycle d'exécution du graph
LangGraph. Aucune persistance cross-run, aucun cache process-wide.

Clé : ``f"{thread_id}:{sha256(query)}"`` (US5 défense en profondeur :
deux threads avec la même query partagent quand même rien).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.embeddings_client import hash_query

if TYPE_CHECKING:
    from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def make_key(thread_id: str | object, query: str) -> str:
    """Construit la clé de cache embedding (US5 : préfixée par thread_id)."""
    return f"{thread_id}:{hash_query(query)}"


def get_cached(state: AgentState, thread_id: str | object, query: str) -> list[float] | None:
    """Retourne l'embedding mis en cache pour ce ``(thread_id, query)`` ou None."""
    key = make_key(thread_id, query)
    return state.embedding_cache.get(key)


def set_cached(
    state: AgentState, thread_id: str | object, query: str, vector: list[float]
) -> None:
    """Met en cache l'embedding pour ce ``(thread_id, query)``."""
    key = make_key(thread_id, query)
    state.embedding_cache[key] = list(vector)


async def get_or_compute(
    state: AgentState,
    *,
    thread_id: str | object,
    query: str,
    embed_fn=None,
) -> list[float] | None:
    """Retourne (ou calcule) l'embedding de ``query`` pour ce ``thread_id``.

    Args:
        state: ``AgentState`` du tour courant — le cache vit ici.
        thread_id: identifiant du thread (composite ou UUID).
        query: texte à embedder.
        embed_fn: callable optionnel pour injection (tests). Default :
            ``app.embeddings_client.embed`` qui hit Voyage.

    Returns:
        Vecteur (list[float] de dim 1024) ou None si Voyage est indisponible
        (mode dégradé FR-014).
    """
    cached = get_cached(state, thread_id, query)
    if cached is not None:
        logger.debug("embedding_cache HIT thread=%s", thread_id)
        return cached

    embed = embed_fn
    if embed is None:
        # Import paresseux pour éviter cycle + faciliter mock dans tests
        from app.embeddings_client import embed as default_embed

        embed = default_embed

    try:
        vectors = embed([query.strip()])
    except Exception as exc:  # noqa: BLE001
        logger.warning("F57 embedding failed (degraded mode): %s", exc)
        return None
    if not vectors:
        return None
    vec = list(vectors[0])
    set_cached(state, thread_id, query, vec)
    return vec


__all__ = [
    "get_cached",
    "get_or_compute",
    "make_key",
    "set_cached",
]
