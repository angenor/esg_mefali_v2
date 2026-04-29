"""F13 — BackgroundTask pour calculer l'embedding Voyage AI d'un message.

Non bloquant (FR-008/FR-026). Failure → row reste avec ``embedding=NULL``.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.chat import repository as repo
from app.db import SessionLocal

logger = logging.getLogger(__name__)


def compute_and_store_embedding(message_id: UUID, content: str) -> None:
    """Appelé en BackgroundTask. Ne lève jamais."""
    if not content or not content.strip():
        return
    try:
        from app.embeddings_client import embed

        vectors = embed([content])
        if not vectors:
            return
        db = SessionLocal()
        try:
            repo.update_message_embedding(
                db, message_id=message_id, embedding=list(vectors[0])
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning(
            "F13 embedding task failed for message=%s: %s", message_id, exc
        )
