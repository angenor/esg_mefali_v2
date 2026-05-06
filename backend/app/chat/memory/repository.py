"""F57 — Repository helpers pour les endpoints memory (RLS-aware).

Toutes les requêtes filtrent strictement par ``thread_id`` ET ``account_id``
(P2 + anti-fuite cross-thread). On positionne aussi le GUC
``app.current_account_id`` au niveau session pour que les RLS policies
de ``chat_message`` / ``chat_thread`` s'appliquent en défense en profondeur.

Référence : ``specs/057-agent-memory-rag/data-model.md`` §4 et
``contracts/memory-endpoint.md``.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_thread_for_account(
    db: Session, *, thread_id: UUID, account_id: UUID
) -> dict[str, Any] | None:
    """Retourne ``{id, summary, last_compacted_at}`` pour le thread ou None.

    Filtre par account_id en plus de l'id (cross-tenant ⇒ None ⇒ 404 logique).
    """
    row = db.execute(
        text(
            """
            SELECT id, summary, last_compacted_at, archived
            FROM chat_thread
            WHERE id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id)},
    ).mappings().first()
    return dict(row) if row else None


def count_messages(
    db: Session, *, thread_id: UUID, account_id: UUID, only_non_compacted: bool = False
) -> int:
    """Compte les messages user/assistant non supprimés du thread."""
    sql = """
        SELECT COUNT(*) AS c
        FROM chat_message
        WHERE thread_id = CAST(:tid AS UUID)
          AND account_id = CAST(:aid AS UUID)
          AND deleted_at IS NULL
          AND role IN ('user', 'assistant')
    """
    if only_non_compacted:
        sql += " AND compacted = FALSE"
    row = db.execute(
        text(sql),
        {"tid": str(thread_id), "aid": str(account_id)},
    ).first()
    return int(row[0]) if row else 0


def count_messages_with_embedding(
    db: Session, *, thread_id: UUID, account_id: UUID
) -> int:
    """Compte les messages indexés (``embedding IS NOT NULL``) du thread."""
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS c
            FROM chat_message
            WHERE thread_id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
              AND embedding IS NOT NULL
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id)},
    ).first()
    return int(row[0]) if row else 0


def get_entities_referenced(
    db: Session, *, thread_id: UUID, account_id: UUID, limit: int = 50
) -> list[dict[str, Any]]:
    """Extrait les entités référencées dans les payloads JSONB du thread.

    On lit ``payload_json->>'entity_type'``, ``payload_json->>'entity_id'``
    et ``payload_json->>'entity_label'`` quand présents (convention F55
    mutation_handlers : tool_call_log + chat_message stockent un
    ``entity_refs`` ou directement les champs ``entity_type/entity_id``).

    Pour le MVP F57 on extrait depuis ``chat_message.payload_json`` quand
    ces clés existent. La liste est dédupliquée par (type, id) en gardant
    le premier label rencontré.
    """
    rows = db.execute(
        text(
            """
            SELECT
                payload_json->>'entity_type' AS etype,
                payload_json->>'entity_id'   AS eid,
                payload_json->>'entity_label' AS elabel
            FROM chat_message
            WHERE thread_id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
              AND payload_json IS NOT NULL
              AND payload_json ? 'entity_type'
              AND payload_json ? 'entity_id'
            ORDER BY created_at DESC
            LIMIT :lim
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id), "lim": int(limit)},
    ).all()
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        etype = r[0]
        eid = r[1]
        elabel = r[2] or ""
        if not etype or not eid:
            continue
        if etype not in {"Entreprise", "Projet", "Candidature", "Indicateur"}:
            continue
        key = (etype, eid)
        if key not in seen:
            seen[key] = {"type": etype, "id": eid, "label": elabel}
    return list(seen.values())


def purge_thread_embeddings(
    db: Session, *, thread_id: UUID, account_id: UUID
) -> int:
    """Set ``chat_message.embedding = NULL`` pour tous les messages du thread.

    Retourne le nombre de rows mises à NULL (= comptage avant purge).

    NE TOUCHE PAS ``chat_message.content`` (P3 audit append-only).
    """
    # Compte d'abord (pour reporting)
    before = db.execute(
        text(
            """
            SELECT COUNT(*) FROM chat_message
            WHERE thread_id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND embedding IS NOT NULL
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id)},
    ).scalar()
    db.execute(
        text(
            """
            UPDATE chat_message SET embedding = NULL
            WHERE thread_id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND embedding IS NOT NULL
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id)},
    )
    return int(before or 0)


def clear_thread_summary(
    db: Session, *, thread_id: UUID, account_id: UUID
) -> tuple[bool, bool]:
    """Set ``chat_thread.summary = NULL`` et ``last_compacted_at = NULL``.

    Retourne ``(summary_was_set, last_compaction_was_set)`` AVANT clear pour
    permettre au caller de signaler ce qui a effectivement été purgé.
    """
    row = db.execute(
        text(
            """
            SELECT summary IS NOT NULL, last_compacted_at IS NOT NULL
            FROM chat_thread
            WHERE id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id)},
    ).first()
    if not row:
        return (False, False)
    summary_was_set = bool(row[0])
    compaction_was_set = bool(row[1])
    db.execute(
        text(
            """
            UPDATE chat_thread
               SET summary = NULL, last_compacted_at = NULL
            WHERE id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id)},
    )
    return (summary_was_set, compaction_was_set)


def write_audit_memory_forget(
    db: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    user_id: UUID,
    embeddings_purged: int,
    summary_was_set: bool,
) -> UUID:
    """Insère une ligne audit_log pour le forget RGPD (P3, FR-019).

    Retourne l'UUID de la ligne audit créée.
    """
    audit_id = uuid4()
    db.execute(
        text(
            """
            INSERT INTO audit_log
                (id, user_id, account_id, entity_type, entity_id,
                 field, old_value, new_value, source_of_change,
                 "timestamp", created_at, updated_at, version)
            VALUES
                (CAST(:id AS UUID), CAST(:uid AS UUID), CAST(:aid AS UUID),
                 'ChatThread', CAST(:tid AS UUID),
                 'memory', CAST(:old AS JSONB), CAST(:new AS JSONB),
                 CAST('memory_system' AS source_of_change_t),
                 now(), now(), now(), 1)
            """
        ),
        {
            "id": str(audit_id),
            "uid": str(user_id),
            "aid": str(account_id),
            "tid": str(thread_id),
            "old": json.dumps(
                {
                    "embeddings_indexed": int(embeddings_purged),
                    "summary_present": bool(summary_was_set),
                }
            ),
            "new": json.dumps({"action": "memory_forget"}),
        },
    )
    return audit_id


def get_or_create_entity_memory(
    db: Session,
    *,
    account_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> dict[str, Any] | None:
    """Retourne la ligne ``agent_entity_memory`` pour ce tuple ou None."""
    row = db.execute(
        text(
            """
            SELECT id, summary, sources_used, last_updated_at, version
            FROM agent_entity_memory
            WHERE account_id = CAST(:aid AS UUID)
              AND entity_type = :etype
              AND entity_id = CAST(:eid AS UUID)
            """
        ),
        {
            "aid": str(account_id),
            "etype": entity_type,
            "eid": str(entity_id),
        },
    ).mappings().first()
    return dict(row) if row else None


def upsert_entity_memory(
    db: Session,
    *,
    account_id: UUID,
    entity_type: str,
    entity_id: UUID,
    summary: str,
    sources_used: list[Any],
) -> tuple[UUID, int]:
    """UPSERT agent_entity_memory ; ON CONFLICT incrémente version.

    Retourne ``(id, version)`` après l'UPSERT.
    """
    row = db.execute(
        text(
            """
            INSERT INTO agent_entity_memory
                (account_id, entity_type, entity_id, summary, sources_used,
                 last_updated_at, version)
            VALUES
                (CAST(:aid AS UUID), :etype, CAST(:eid AS UUID),
                 :summary, CAST(:sources AS JSONB), now(), 1)
            ON CONFLICT (account_id, entity_type, entity_id) DO UPDATE
              SET summary = EXCLUDED.summary,
                  sources_used = EXCLUDED.sources_used,
                  last_updated_at = now(),
                  version = agent_entity_memory.version + 1
            RETURNING id, version
            """
        ),
        {
            "aid": str(account_id),
            "etype": entity_type,
            "eid": str(entity_id),
            "summary": summary,
            "sources": json.dumps(sources_used or []),
        },
    ).first()
    if row is None:
        raise RuntimeError("UPSERT agent_entity_memory returned no row")
    return (UUID(str(row[0])), int(row[1]))


def delete_entity_memory(
    db: Session,
    *,
    account_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> int:
    """Supprime la ligne ``agent_entity_memory`` correspondante. Retourne le
    nombre de rows supprimées (0 ou 1)."""
    result = db.execute(
        text(
            """
            DELETE FROM agent_entity_memory
            WHERE account_id = CAST(:aid AS UUID)
              AND entity_type = :etype
              AND entity_id = CAST(:eid AS UUID)
            """
        ),
        {
            "aid": str(account_id),
            "etype": entity_type,
            "eid": str(entity_id),
        },
    )
    return int(result.rowcount or 0)


def write_audit_entity_memory(
    db: Session,
    *,
    account_id: UUID,
    entity_type: str,
    entity_id: UUID,
    user_id: UUID | None,
    operation: str,
    version: int | None,
    agent_run_id: UUID | None = None,
) -> UUID:
    """Insère une ligne audit pour CRUD entity_memory (P3, FR-019).

    ``operation`` ∈ ``upsert`` | ``delete``.
    """
    audit_id = uuid4()
    db.execute(
        text(
            """
            INSERT INTO audit_log
                (id, user_id, account_id, entity_type, entity_id,
                 field, old_value, new_value, source_of_change,
                 agent_run_id, "timestamp", created_at, updated_at, version)
            VALUES
                (CAST(:id AS UUID), CAST(:uid AS UUID), CAST(:aid AS UUID),
                 'AgentEntityMemory', CAST(:eid AS UUID),
                 :field, CAST(:old AS JSONB), CAST(:new AS JSONB),
                 CAST('memory_system' AS source_of_change_t),
                 CAST(:rid AS UUID), now(), now(), now(), 1)
            """
        ),
        {
            "id": str(audit_id),
            "uid": str(user_id) if user_id else None,
            "aid": str(account_id),
            "eid": str(entity_id),
            "field": f"entity_memory:{entity_type}",
            "old": None,
            "new": json.dumps({"operation": operation, "version": version}),
            "rid": str(agent_run_id) if agent_run_id else None,
        },
    )
    return audit_id


__all__ = [
    "clear_thread_summary",
    "count_messages",
    "count_messages_with_embedding",
    "delete_entity_memory",
    "get_entities_referenced",
    "get_or_create_entity_memory",
    "get_thread_for_account",
    "purge_thread_embeddings",
    "upsert_entity_memory",
    "write_audit_entity_memory",
    "write_audit_memory_forget",
]
