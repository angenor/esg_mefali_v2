"""F56 — Handler READ ``search_source`` (FR-004).

Recherche sémantique sur ``source.embedding`` filtrée
``verification_status='verified'``. Utilise Voyage ``voyage-3.5`` (1024 dim)
pour embedder la query, puis cosine sur ``source.embedding`` via pgvector.

Sur indisponibilité Voyage → fallback ``ILIKE`` sur ``title`` / ``section`` /
``publisher``, retour ``degraded=True``.

Sur 0 résultat → liste vide + ``hint='no_match'`` (suggestion implicite
au LLM d'envisager ``flag_unsourced``).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.state import AgentState, ValidatedToolCall

logger = logging.getLogger(__name__)


def _get_session(state: AgentState) -> Session | None:
    try:
        from app.db import SessionLocal
    except Exception:  # pragma: no cover
        return None
    db = SessionLocal()
    try:
        db.execute(
            text(
                f"SET LOCAL \"app.current_account_id\" = '{state.account_id}'"
            )
        )
    except Exception:  # pragma: no cover
        pass
    return db


def _format_results(rows) -> list[dict[str, Any]]:
    return [
        {
            "id": str(r["id"]),
            "title": r.get("title"),
            "publisher": r.get("publisher"),
            "url": r.get("canonical_url") or r.get("url"),
            "page": r.get("page"),
            "section": r.get("section"),
            "snippet": r.get("snippet"),
            "score": float(r["score"]) if r.get("score") is not None else None,
        }
        for r in rows
    ]


async def search_source_handler(
    state: AgentState, call: ValidatedToolCall
) -> dict[str, Any]:
    """Cherche jusqu'à ``limit`` sources verifiées matchant ``query``.

    Args:
        state: AgentState.
        call: ValidatedToolCall (``arguments.query``, ``arguments.limit``).

    Returns:
        dict :
        - ``{"results": [...], "degraded": False}`` (Voyage OK)
        - ``{"results": [...], "degraded": True}`` (fallback ILIKE)
        - ``{"results": [], "degraded": False, "hint": "no_match — consider flag_unsourced"}``
    """
    args = call.arguments
    query = getattr(args, "query", "") or ""
    limit = int(getattr(args, "limit", 5) or 5)

    if not query.strip():
        return {"results": [], "degraded": False, "hint": "empty_query"}

    db = _get_session(state)
    if db is None:
        return {"results": [], "degraded": True, "hint": "db_unavailable"}

    # Étape 1 — Tentative d'embedding via Voyage
    embedding: list[float] | None = None
    try:
        from app.embeddings_client import VoyageError, embed

        try:
            embeddings = embed([query])
            if embeddings:
                embedding = embeddings[0]
        except (RuntimeError, VoyageError) as exc:
            logger.info("Voyage unavailable, fallback ILIKE: %s", exc)
            embedding = None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Voyage embedding failed unexpectedly: %s", exc)
            embedding = None
    except Exception as exc:  # noqa: BLE001 - import failure
        logger.warning("embeddings module unavailable: %s", exc)
        embedding = None

    try:
        if embedding is not None:
            try:
                rows = (
                    db.execute(
                        text(
                            "SELECT id, title, publisher, url, canonical_url, "
                            "page, section, "
                            "LEFT(COALESCE(notes, ''), 200) AS snippet, "
                            "1 - (embedding <=> CAST(:e AS vector)) AS score "
                            "FROM source "
                            "WHERE verification_status = 'verified' "
                            "AND embedding IS NOT NULL "
                            "ORDER BY embedding <=> CAST(:e AS vector) ASC "
                            "LIMIT :limit"
                        ),
                        {"e": str(embedding), "limit": limit},
                    )
                    .mappings()
                    .all()
                )
                results = _format_results(rows)
                if not results:
                    return {
                        "results": [],
                        "degraded": False,
                        "hint": "no_match — consider flag_unsourced",
                    }
                return {"results": results, "degraded": False}
            except Exception as exc:  # noqa: BLE001
                logger.info("pgvector cosine query failed, fallback ILIKE: %s", exc)
                # tomber sur ILIKE

        # Fallback ILIKE
        like_q = f"%{query}%"
        rows = (
            db.execute(
                text(
                    "SELECT id, title, publisher, url, canonical_url, "
                    "page, section, "
                    "LEFT(COALESCE(notes, ''), 200) AS snippet, "
                    "NULL::float AS score "
                    "FROM source "
                    "WHERE verification_status = 'verified' "
                    "AND ("
                    "  title ILIKE :q "
                    "  OR section ILIKE :q "
                    "  OR publisher ILIKE :q"
                    ") "
                    "ORDER BY length(title) ASC "
                    "LIMIT :limit"
                ),
                {"q": like_q, "limit": limit},
            )
            .mappings()
            .all()
        )
        results = _format_results(rows)
        if not results:
            return {
                "results": [],
                "degraded": True,
                "hint": "no_match — consider flag_unsourced",
            }
        return {"results": results, "degraded": True}
    finally:
        try:
            db.close()
        except Exception:  # pragma: no cover
            pass


__all__ = ["search_source_handler"]
