"""F57 — Recherche cosine pgvector intra-thread (US1 long terme + US2 tool).

Toutes les requêtes scope strict ``thread_id`` ET ``account_id`` (P2 +
anti-fuite cross-thread, US5). RLS GUC ``app.current_account_id`` doit
être positionné par le caller (middleware F02 ou helper agent).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

#: Seuil "tool" : 0.0 (le LLM a explicitement demandé, on ne filtre pas).
TOOL_DEFAULT_THRESHOLD: float = 0.0


@dataclass(frozen=True)
class LongTermMatch:
    """Résultat d'une recherche cosine pgvector — immuable."""

    message_id: UUID
    role: str
    content: str
    created_at: datetime
    score: float


def _conv_uuid_from_thread_id(thread_id: str | UUID) -> str | None:
    """Extrait l'UUID conversation depuis ``thread_id``.

    F57 supporte deux formats :
    - composite ``{account_uuid}:{conv_uuid}`` (F53/F54/F55) → retourne le suffixe.
    - UUID simple (legacy F18) → retourne tel quel.
    """
    if isinstance(thread_id, UUID):
        return str(thread_id)
    s = str(thread_id)
    if ":" in s:
        _, _, suffix = s.partition(":")
        return suffix or None
    return s


def search_long_term(
    db: Session,
    *,
    thread_id: str | UUID,
    account_id: UUID,
    query_embedding: list[float],
    exclude_message_ids: list[str] | None = None,
    limit: int = 3,
    threshold: float = 0.7,
    only_non_compacted: bool = True,
) -> list[LongTermMatch]:
    """Cosine search top-K sur les messages anciens du thread courant.

    Args:
        db: session SQLAlchemy avec RLS GUC positionné.
        thread_id: thread courant (composite ``{a}:{c}`` ou UUID simple).
        account_id: account courant (filtre explicite + RLS).
        query_embedding: vecteur 1024 dim de la query (Voyage).
        exclude_message_ids: IDs déjà présents dans le contexte court terme
            (15 derniers) à exclure de la recherche.
        limit: top-K (US1: 3 ; US2 LLM-driven: 1-10).
        threshold: similarité cosine min ; 0.0 désactive (US2 tool).
        only_non_compacted: True (défaut) exclut les messages déjà compactés.

    Returns:
        Liste ordonnée par similarité décroissante. Vide si fallback.
    """
    if not query_embedding:
        return []

    conv_uuid = _conv_uuid_from_thread_id(thread_id)
    if not conv_uuid:
        return []

    excluded = list(exclude_message_ids or [])
    has_exclusion = bool(excluded)

    sql = text(
        """
        SELECT id, role, content, created_at,
               1 - (embedding <=> CAST(:qvec AS vector)) AS score
        FROM chat_message
        WHERE thread_id = CAST(:tid AS UUID)
          AND account_id = CAST(:aid AS UUID)
          AND embedding IS NOT NULL
          AND deleted_at IS NULL
          AND role IN ('user', 'assistant')
          AND (CAST(:nc AS BOOLEAN) IS FALSE OR compacted = FALSE)
          AND (CAST(:has_excl AS BOOLEAN) IS FALSE OR id NOT IN :excl)
          AND (1 - (embedding <=> CAST(:qvec AS vector))) >= :threshold
        ORDER BY embedding <=> CAST(:qvec AS vector) ASC
        LIMIT :k
        """
    ).bindparams(bindparam("excl", expanding=True))

    params: dict[str, Any] = {
        "tid": conv_uuid,
        "aid": str(account_id),
        "qvec": list(query_embedding),
        "nc": bool(only_non_compacted),
        "has_excl": has_exclusion,
        "excl": excluded or ["00000000-0000-0000-0000-000000000000"],
        "threshold": float(threshold),
        "k": int(limit),
    }
    try:
        rows = db.execute(sql, params).mappings().all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("F57 pgvector search failed (degraded): %s", exc)
        return []
    out: list[LongTermMatch] = []
    for r in rows:
        try:
            mid = UUID(str(r["id"]))
        except Exception:  # noqa: BLE001
            continue
        out.append(
            LongTermMatch(
                message_id=mid,
                role=str(r.get("role") or ""),
                content=str(r.get("content") or ""),
                created_at=r["created_at"],
                score=float(r.get("score") or 0.0),
            )
        )
    return out


def fetch_recent_message_ids(
    db: Session,
    *,
    thread_id: str | UUID,
    account_id: UUID,
    limit: int = 15,
) -> list[str]:
    """Retourne les IDs des ``limit`` derniers messages chronologiques."""
    conv_uuid = _conv_uuid_from_thread_id(thread_id)
    if not conv_uuid:
        return []
    rows = db.execute(
        text(
            """
            SELECT id
            FROM chat_message
            WHERE thread_id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND role IN ('user', 'assistant')
              AND deleted_at IS NULL
              AND compacted = FALSE
            ORDER BY created_at DESC
            LIMIT :lim
            """
        ),
        {"tid": conv_uuid, "aid": str(account_id), "lim": int(limit)},
    ).all()
    return [str(r[0]) for r in rows]


def fetch_recent_messages(
    db: Session,
    *,
    thread_id: str | UUID,
    account_id: UUID,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Retourne les ``limit`` derniers messages (asc chronologique).

    Exclut ``compacted=True`` et ``deleted_at IS NOT NULL``.
    """
    conv_uuid = _conv_uuid_from_thread_id(thread_id)
    if not conv_uuid:
        return []
    rows = db.execute(
        text(
            """
            SELECT id, role, content, created_at
            FROM chat_message
            WHERE thread_id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND role IN ('user', 'assistant')
              AND deleted_at IS NULL
              AND compacted = FALSE
            ORDER BY created_at DESC
            LIMIT :lim
            """
        ),
        {"tid": conv_uuid, "aid": str(account_id), "lim": int(limit)},
    ).mappings().all()
    return list(reversed([dict(r) for r in rows]))


def count_thread_messages(
    db: Session,
    *,
    thread_id: str | UUID,
    account_id: UUID,
    only_non_compacted: bool = True,
) -> int:
    """Compte les messages user/assistant non supprimés du thread."""
    conv_uuid = _conv_uuid_from_thread_id(thread_id)
    if not conv_uuid:
        return 0
    sql = """
        SELECT COUNT(*) FROM chat_message
        WHERE thread_id = CAST(:tid AS UUID)
          AND account_id = CAST(:aid AS UUID)
          AND deleted_at IS NULL
          AND role IN ('user', 'assistant')
    """
    if only_non_compacted:
        sql += " AND compacted = FALSE"
    row = db.execute(
        text(sql),
        {"tid": conv_uuid, "aid": str(account_id)},
    ).first()
    return int(row[0]) if row else 0


__all__ = [
    "LongTermMatch",
    "TOOL_DEFAULT_THRESHOLD",
    "count_thread_messages",
    "fetch_recent_message_ids",
    "fetch_recent_messages",
    "search_long_term",
]
