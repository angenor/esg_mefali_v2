"""F57 — Service layer pour ``GET`` / ``DELETE /me/chat/threads/{id}/memory``.

Source de vérité : ``backend/app/chat/memory/repository.py`` pour les
helpers RLS-aware. Ce module agrège ``MemorySnapshotV2`` (US3) et
implémente ``forget_thread_memory`` (US4) en transaction synchronisée.

Référence : ``specs/057-agent-memory-rag/contracts/memory-endpoint.md`` et
``data-model.md`` §4.2.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.chat.memory.repository import (
    clear_thread_summary,
    count_messages,
    count_messages_with_embedding,
    get_entities_referenced,
    get_thread_for_account,
    purge_thread_embeddings,
    write_audit_memory_forget,
)
from app.chat.memory.schemas import (
    EntityRef,
    ForgetMemoryResult,
    MemorySnapshotV2,
)
from app.config import get_settings

logger = logging.getLogger(__name__)


class ThreadMemoryNotFoundError(LookupError):
    """Le thread n'existe pas pour ce compte (P2 → 404)."""


def get_memory_snapshot(
    db: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
) -> MemorySnapshotV2:
    """Construit ``MemorySnapshotV2`` (US3, FR-007).

    Raises:
        ThreadMemoryNotFoundError: si thread inexistant ou cross-tenant (P2).
    """
    thread = get_thread_for_account(
        db, thread_id=thread_id, account_id=account_id
    )
    if thread is None:
        raise ThreadMemoryNotFoundError("thread_not_found")

    settings = get_settings()
    recent_count = int(settings.LLM_AGENT_MEMORY_RECENT_COUNT)

    total = count_messages(
        db, thread_id=thread_id, account_id=account_id, only_non_compacted=False
    )
    indexed = count_messages_with_embedding(
        db, thread_id=thread_id, account_id=account_id
    )
    entities_raw = get_entities_referenced(
        db, thread_id=thread_id, account_id=account_id
    )

    entities: list[EntityRef] = []
    for ent in entities_raw:
        try:
            entities.append(
                EntityRef(
                    type=ent["type"],
                    id=UUID(str(ent["id"])),
                    label=str(ent.get("label") or ""),
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("snapshot: skip invalid entity ref: %s", exc)
            continue

    return MemorySnapshotV2(
        total_messages=int(total),
        recent_messages_count=min(int(total), recent_count),
        summary=thread.get("summary"),
        vector_index_size=int(indexed),
        last_compaction_at=thread.get("last_compacted_at"),
        entities_referenced=entities,
    )


def forget_thread_memory(
    db: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    user_id: UUID,
) -> ForgetMemoryResult:
    """Purge synchrone des artefacts mémoire (US4, FR-008).

    1. ``UPDATE chat_message SET embedding = NULL`` (RLS).
    2. ``UPDATE chat_thread SET summary = NULL, last_compacted_at = NULL``.
    3. ``INSERT audit_log`` (P3, ``source_of_change='memory_system'``).

    NE TOUCHE PAS :
    - ``chat_message.content`` (P3 audit append-only).
    - ``agent_entity_memory`` (account-wide, Q3 clarification).
    - ``recall_log`` (historique tracing).

    Idempotent : un second appel retourne ``embeddings_purged=0``.

    Raises:
        ThreadMemoryNotFoundError: si thread inexistant ou cross-tenant.
    """
    thread = get_thread_for_account(
        db, thread_id=thread_id, account_id=account_id
    )
    if thread is None:
        raise ThreadMemoryNotFoundError("thread_not_found")

    embeddings_purged = purge_thread_embeddings(
        db, thread_id=thread_id, account_id=account_id
    )
    summary_was_set, compaction_was_set = clear_thread_summary(
        db, thread_id=thread_id, account_id=account_id
    )
    audit_id = write_audit_memory_forget(
        db,
        thread_id=thread_id,
        account_id=account_id,
        user_id=user_id,
        embeddings_purged=embeddings_purged,
        summary_was_set=summary_was_set,
    )
    messages_kept = count_messages(
        db, thread_id=thread_id, account_id=account_id, only_non_compacted=False
    )

    return ForgetMemoryResult(
        thread_id=thread_id,
        embeddings_purged=int(embeddings_purged),
        summary_cleared=bool(summary_was_set),
        last_compaction_cleared=bool(compaction_was_set),
        messages_kept_for_audit=int(messages_kept),
        agent_entity_memory_unchanged=True,
        audit_log_id=audit_id,
    )


__all__ = [
    "ThreadMemoryNotFoundError",
    "forget_thread_memory",
    "get_memory_snapshot",
]
