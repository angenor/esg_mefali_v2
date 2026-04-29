"""F13 / F18 — BackgroundTask pour calculer l'embedding Voyage AI d'un message.

Non bloquant : en cas d'échec Voyage, le row reste avec ``embedding=NULL``
(FR-007 — la conversation ne doit jamais être bloquée).

F18 (FR-008) : pour les messages tool (visualisation, action), on embedde
le label / titre humain du payload plutôt que le JSON brut.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.chat import repository as repo
from app.db import SessionLocal

logger = logging.getLogger(__name__)


def compute_and_store_embedding(
    message_id: UUID,
    content: str,
    payload_json: dict[str, Any] | None = None,
) -> None:
    """Appelé en BackgroundTask. Ne lève jamais.

    Args:
        message_id: identifiant du message à enrichir.
        content: texte brut du message (peut être vide pour un payload pur).
        payload_json: payload tool éventuel — si présent et qu'il contient
            un label/title humain, c'est ce texte qui est embeddé (F18).
    """
    try:
        from app.chat.memory.compactors import extract_embedding_text

        text_to_embed = extract_embedding_text(content or "", payload_json)
    except Exception:
        text_to_embed = content or ""

    if not text_to_embed or not text_to_embed.strip():
        return

    try:
        from app.embeddings_client import embed

        vectors = embed([text_to_embed])
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
