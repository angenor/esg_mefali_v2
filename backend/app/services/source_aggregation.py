"""F56 / T044 (US8) — Agrégation des sources d'un thread chat.

Helper utilisé par F49 (génération PDF "Sources et références") pour
collecter, dédupliquer et numéroter les sources citées dans un thread.

API :

    aggregate_thread_sources(db, thread_id) -> list[dict]

Retourne une liste de dicts ``SourceRef`` (cf.
``contracts/sse-events.md`` §SourceRef) :
- triés par ``citation_index`` croissant (ordre de première apparition),
- dédupliqués par ``source_id``,
- agrège tous les ``chat_message.sources`` du thread.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def aggregate_thread_sources(
    db: Session, thread_id: UUID
) -> list[dict[str, Any]]:
    """Agrège les sources uniques citées dans un thread.

    Args:
        db: Session SQLAlchemy active (RLS context attendu côté caller).
        thread_id: UUID du thread chat.

    Returns:
        Liste de dicts ``SourceRef``-compatibles, triés par première
        apparition (``citation_index`` re-numéroté de 1 à N).
    """
    rows = (
        db.execute(
            text(
                """
                SELECT m.id AS message_id, m.created_at AS msg_created_at,
                       m.sources
                FROM chat_message m
                WHERE m.thread_id = CAST(:tid AS UUID)
                  AND m.sources IS NOT NULL
                ORDER BY m.created_at ASC, m.id ASC
                """
            ),
            {"tid": str(thread_id)},
        )
        .mappings()
        .all()
    )

    seen: dict[str, dict[str, Any]] = {}
    next_index = 1
    for row in rows:
        sources_value = row.get("sources") or []
        if not isinstance(sources_value, list):
            continue
        for src in sources_value:
            if not isinstance(src, dict):
                continue
            sid = src.get("source_id")
            if not sid:
                continue
            sid_str = str(sid)
            if sid_str in seen:
                continue
            entry = dict(src)
            entry["source_id"] = sid_str
            entry["citation_index"] = next_index
            seen[sid_str] = entry
            next_index += 1
    # Préserve l'ordre d'insertion (Python 3.7+).
    return list(seen.values())


__all__ = ["aggregate_thread_sources"]
