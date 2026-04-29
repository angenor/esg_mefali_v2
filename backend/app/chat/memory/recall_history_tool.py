"""F18 — Tool ``recall_history`` (P2).

Recherche pgvector intra-thread sur les messages user/assistant antérieurs
aux 15 derniers (FR-006, FR-011, FR-012, FR-015, FR-016).

Le tool est enregistré dans :mod:`app.orchestrator.tool_registry` à
l'import du module — voir :func:`_register_tool`. L'enregistrement n'a
lieu qu'une seule fois et est idempotent (silencieux si déjà présent).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.chat.memory.compactors import extract_embedding_text

logger = logging.getLogger(__name__)

MIN_QUERY_CHARS: int = 3
DEFAULT_K: int = 5
MAX_K: int = 10
SNIPPET_MAX_CHARS: int = 240
RECENT_EXCLUSION_LIMIT: int = 15


class RecallHistoryArgs(BaseModel):
    """Schéma strict (extra='forbid') du tool ``recall_history``."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=DEFAULT_K, ge=1, le=MAX_K)


class RecallHit(BaseModel):
    """Élément retourné par le tool — schéma strict."""

    model_config = ConfigDict(extra="forbid")

    message_id: UUID
    thread_id: UUID
    role: Literal["user", "assistant"]
    snippet: str
    created_at: datetime
    similarity: float


def _make_snippet(content: str, payload_json: dict[str, Any] | None) -> str:
    """Construit un snippet concis à partir du content / payload."""
    text_value = extract_embedding_text(content or "", payload_json) or (content or "")
    text_value = text_value.strip()
    if len(text_value) <= SNIPPET_MAX_CHARS:
        return text_value
    return text_value[: SNIPPET_MAX_CHARS - 1].rstrip() + "…"


def _embed_query(query: str) -> list[float] | None:
    """Calcule l'embedding Voyage pour la query. Retourne None en cas d'échec."""
    try:
        from app.embeddings_client import embed

        vectors = embed([query.strip()])
    except Exception as exc:
        logger.warning("F18 recall_history: embed query failed: %s", exc)
        return None
    if not vectors:
        return None
    return list(vectors[0])


def _fetch_recent_message_ids(
    db: Session, *, thread_id: UUID, account_id: UUID, limit: int
) -> list[str]:
    """Récupère les IDs des ``limit`` derniers messages user/assistant."""
    rows = db.execute(
        text(
            """
            SELECT id
            FROM chat_message
            WHERE thread_id = :tid AND account_id = :aid
              AND role IN ('user', 'assistant')
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id), "limit": int(limit)},
    ).all()
    return [str(r[0]) for r in rows]


def execute_recall_history(
    db: Session,
    *,
    account_id: UUID,
    thread_id: UUID,
    args: RecallHistoryArgs,
) -> list[RecallHit]:
    """Exécute le tool ``recall_history``.

    Args:
        db: session SQLAlchemy (RLS positionnée).
        account_id: compte courant (filtre RLS + explicite).
        thread_id: thread courant (intra-thread uniquement, FR-012).
        args: arguments validés Pydantic.

    Returns:
        Liste ordonnée par similarité décroissante (max ``args.k``). Vide
        si query < 3 chars (FR-016) ou si Voyage indisponible.
    """
    cleaned = (args.query or "").strip()
    if len(cleaned) < MIN_QUERY_CHARS:
        return []

    qvec = _embed_query(cleaned)
    if qvec is None:
        return []

    recent_ids = _fetch_recent_message_ids(
        db,
        thread_id=thread_id,
        account_id=account_id,
        limit=RECENT_EXCLUSION_LIMIT,
    )

    sql = text(
        """
        SELECT id, thread_id, role, content, payload_json, created_at,
               1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
        FROM chat_message
        WHERE account_id = :aid
          AND thread_id = :tid
          AND embedding IS NOT NULL
          AND deleted_at IS NULL
          AND role IN ('user', 'assistant')
          AND (CAST(:has_recent AS BOOLEAN) IS FALSE OR id NOT IN :recent_ids)
        ORDER BY embedding <=> CAST(:qvec AS vector) ASC
        LIMIT :k
        """
    ).bindparams(bindparam("recent_ids", expanding=True))

    params: dict[str, Any] = {
        "aid": str(account_id),
        "tid": str(thread_id),
        "qvec": qvec,
        "has_recent": bool(recent_ids),
        "recent_ids": recent_ids or ["00000000-0000-0000-0000-000000000000"],
        "k": int(args.k),
    }

    rows = db.execute(sql, params).mappings().all()
    hits: list[RecallHit] = []
    for row in rows:
        hits.append(
            RecallHit(
                message_id=UUID(str(row["id"])),
                thread_id=UUID(str(row["thread_id"])),
                role=row["role"],  # type: ignore[arg-type]
                snippet=_make_snippet(row.get("content") or "", row.get("payload_json")),
                created_at=row["created_at"],
                similarity=float(row.get("similarity") or 0.0),
            )
        )
    return hits


# --- Enregistrement registry F14 (idempotent) ---


def _register_tool() -> None:
    """Enregistre le tool dans :mod:`app.orchestrator.tool_registry`."""
    try:
        from app.orchestrator import tool_registry as registry
    except Exception as exc:
        logger.debug("F18 recall_history: registry indisponible: %s", exc)
        return

    if "recall_history" in getattr(registry, "TOOL_REGISTRY", {}):
        return

    try:
        registry.tool(
            name="recall_history",
            description=(
                "Recherche dans l'historique ancien de la conversation actuelle "
                "(au-delà des 15 derniers messages) un fragment lié à la question."
            ),
            use_when=(
                "L'utilisateur fait référence à un sujet, projet ou décision "
                "discuté précédemment dans la même conversation et qui "
                "n'apparaît pas dans les 15 derniers messages."
            ),
            dont_use_when=(
                "La réponse se trouve dans les 15 derniers messages, OU "
                "l'utilisateur démarre un nouveau sujet, OU le thread contient "
                "moins de 16 messages."
            ),
            schema=RecallHistoryArgs,
            positive_examples=(
                {"query": "biogaz Sénégal", "k": 5},
                {"query": "ratio CA effectifs"},
            ),
            negative_examples=(
                {"query": ""},
                {"query": "ab"},
            ),
        )
    except Exception as exc:
        logger.warning("F18 recall_history: registry registration failed: %s", exc)


_register_tool()


__all__ = [
    "DEFAULT_K",
    "MAX_K",
    "MIN_QUERY_CHARS",
    "RECENT_EXCLUSION_LIMIT",
    "SNIPPET_MAX_CHARS",
    "RecallHistoryArgs",
    "RecallHit",
    "execute_recall_history",
]
