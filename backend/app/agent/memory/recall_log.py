"""F57 — Tracing recall (US9 / FR-012).

INSERT-only ; UPDATE/DELETE révoqués sur ``app_user`` côté DDL (P3).

Le caller appelle ``stage_recall_log_entry`` (in-memory) pendant le tour
et ``flush_recall_log_entries`` à la fin pour 1 commit DB. Cohérent avec
``AgentState.recall_log_entries`` (transient, exclu du checkpointer).
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def stage_entry(
    *,
    recall_type: str,
    thread_id: str,
    account_id: UUID,
    query_hash: str,
    top_k: int,
    top_scores: list[dict[str, Any]],
    latency_ms: int,
    agent_run_id: UUID | None = None,
) -> dict[str, Any]:
    """Construit une entry recall_log à empiler dans ``state.recall_log_entries``.

    Conserve la même clé pour l'UUID — généré à l'insertion DB par
    ``flush_recall_log_entries`` ou par DEFAULT ``gen_random_uuid()``.
    """
    if recall_type not in ("auto", "tool"):
        raise ValueError(f"recall_type doit être 'auto'|'tool', reçu {recall_type!r}")
    return {
        "recall_type": recall_type,
        "thread_id": str(thread_id),
        "account_id": str(account_id),
        "query_hash": str(query_hash),
        "top_k": int(top_k),
        "top_scores": list(top_scores or []),
        "latency_ms": int(latency_ms),
        "agent_run_id": str(agent_run_id) if agent_run_id else None,
    }


def write_recall_log(
    db: Session,
    *,
    recall_type: str,
    thread_id: str | UUID,
    account_id: UUID,
    query_hash: str,
    top_k: int,
    top_scores: list[dict[str, Any]],
    latency_ms: int,
    agent_run_id: UUID | None = None,
) -> UUID | None:
    """INSERT direct dans ``recall_log``. Retourne l'UUID inséré ou None.

    Best-effort : une erreur log warning ne propage pas (le tour ne doit
    pas casser pour un tracing).
    """
    if recall_type not in ("auto", "tool"):
        raise ValueError(f"recall_type doit être 'auto'|'tool', reçu {recall_type!r}")
    conv_uuid: str
    if isinstance(thread_id, UUID):
        conv_uuid = str(thread_id)
    else:
        s = str(thread_id)
        conv_uuid = s.partition(":")[2] if ":" in s else s
    if not conv_uuid:
        return None
    new_id = uuid4()
    try:
        db.execute(
            text(
                """
                INSERT INTO recall_log
                  (id, agent_run_id, account_id, thread_id, recall_type,
                   query_hash, top_k, top_scores, latency_ms, created_at)
                VALUES
                  (CAST(:id AS UUID), CAST(:rid AS UUID), CAST(:aid AS UUID),
                   CAST(:tid AS UUID), :rt, :qh, :k, CAST(:s AS JSONB), :ms, now())
                """
            ),
            {
                "id": str(new_id),
                "rid": str(agent_run_id) if agent_run_id else None,
                "aid": str(account_id),
                "tid": conv_uuid,
                "rt": recall_type,
                "qh": query_hash,
                "k": int(top_k),
                "s": json.dumps(top_scores or []),
                "ms": int(latency_ms),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("F57 recall_log write failed (best-effort): %s", exc)
        return None
    return new_id


def flush_entries(
    db: Session, entries: list[dict[str, Any]]
) -> int:
    """Bulk INSERT des entries staged. Retourne le nombre de rows écrites.

    Best-effort par entry : une erreur sur une entry n'empêche pas les
    suivantes d'être écrites.
    """
    written = 0
    for e in entries:
        try:
            agent_run_id = e.get("agent_run_id")
            new_id = write_recall_log(
                db,
                recall_type=str(e["recall_type"]),
                thread_id=str(e["thread_id"]),
                account_id=UUID(str(e["account_id"])),
                query_hash=str(e["query_hash"]),
                top_k=int(e["top_k"]),
                top_scores=list(e.get("top_scores") or []),
                latency_ms=int(e.get("latency_ms") or 0),
                agent_run_id=UUID(str(agent_run_id)) if agent_run_id else None,
            )
            if new_id:
                written += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("F57 recall_log entry skipped: %s", exc)
            continue
    return written


__all__ = ["flush_entries", "stage_entry", "write_recall_log"]
