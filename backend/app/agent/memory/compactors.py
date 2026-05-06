"""F57 / US6 — Compaction async des threads ≥ 100 messages.

Comportement :

1. Lock optimiste : ``UPDATE chat_thread SET last_compacted_at = now()
   WHERE id = :tid AND (last_compacted_at IS NULL OR last_compacted_at <
   now() - INTERVAL '60 seconds')``. Le ``WHERE`` empêche deux compactions
   concurrentes (le perdant rowcount=0, abort).
2. Sélectionne les ``LLM_AGENT_COMPACT_BATCH_SIZE`` (=50) messages les
   plus anciens non encore compactés du thread.
3. Appelle le LLM avec un prompt système strict (``≤ LLM_AGENT_COMPACT_MAX_TOKENS``
   = 500). Pas d'invention de chiffres.
4. ``UPDATE chat_thread SET summary = :s, last_compacted_at = now()``.
5. ``UPDATE chat_message SET compacted = TRUE WHERE id = ANY(:ids)``.
6. Audit log ``source_of_change='memory_system'``.

Mode dégradé : LLM down → libère le lock optimiste (last_compacted_at
réinitialisé à NULL) sans muter ``summary`` ; retry au prochain trigger.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings

logger = logging.getLogger(__name__)


def _set_rls_context(session: Session, *, account_id: UUID) -> None:
    try:
        session.execute(
            text(f"SET LOCAL app.current_account_id = '{account_id}'")
        )
    except Exception:  # pragma: no cover
        pass


def _try_acquire_lock(
    session: Session, *, thread_id: UUID, account_id: UUID
) -> bool:
    """Lock optimiste via ``UPDATE … WHERE last_compacted_at IS NULL OR
    last_compacted_at < now() - 60s`` ; retourne True si acquis."""
    res = session.execute(
        text(
            """
            UPDATE chat_thread
               SET last_compacted_at = now()
             WHERE id = CAST(:tid AS UUID)
               AND account_id = CAST(:aid AS UUID)
               AND (last_compacted_at IS NULL OR
                    last_compacted_at < now() - INTERVAL '60 seconds')
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id)},
    )
    return int(res.rowcount or 0) > 0


def _select_batch_message_ids(
    session: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    batch_size: int,
) -> list[str]:
    """Retourne les IDs des ``batch_size`` messages les plus anciens non
    compactés (compacted=FALSE)."""
    rows = session.execute(
        text(
            """
            SELECT id FROM chat_message
            WHERE thread_id = CAST(:tid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
              AND role IN ('user', 'assistant')
              AND compacted = FALSE
            ORDER BY created_at ASC
            LIMIT :n
            """
        ),
        {"tid": str(thread_id), "aid": str(account_id), "n": int(batch_size)},
    ).all()
    return [str(r[0]) for r in rows]


def _fetch_messages_for_summary(
    session: Session, *, message_ids: list[str]
) -> list[dict]:
    """Charge le contenu des messages à résumer (best-effort)."""
    if not message_ids:
        return []
    rows = session.execute(
        text(
            """
            SELECT role, content, created_at FROM chat_message
            WHERE id = ANY(CAST(:ids AS UUID[]))
            ORDER BY created_at ASC
            """
        ),
        {"ids": message_ids},
    ).mappings().all()
    return [dict(r) for r in rows]


def _llm_summarize_messages(
    *, msgs: list[dict], max_tokens: int
) -> str | None:
    """LLM call court pour générer le summary. None si LLM indisponible."""
    if not msgs:
        return None
    sys_p = (
        "Tu rédiges un résumé strictement factuel et compact (<= 500 tokens) "
        "de la conversation suivante entre un agent ESG et un utilisateur PME. "
        "Aucune anecdote ni opinion. Format : 5-15 bullets en français "
        "commençant par '-' avec date au format YYYY-MM-DD si pertinent."
    )
    excerpt_lines = []
    for m in msgs[:200]:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "").strip()
        if not content:
            continue
        excerpt_lines.append(f"[{role}] {content[:600]}")
    user_p = "Conversation à résumer :\n" + "\n".join(excerpt_lines)
    try:
        from app.llm_client import get_llm_client

        settings = get_settings()
        client = get_llm_client()
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": sys_p},
                {"role": "user", "content": user_p},
            ],
            max_tokens=int(max_tokens),
            temperature=0.1,
        )
        choices = getattr(completion, "choices", None) or []
        if not choices:
            return None
        message = getattr(choices[0], "message", None)
        out = getattr(message, "content", None) if message else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("compactor: LLM unavailable (%s)", exc)
        return None
    if not out or not str(out).strip():
        return None
    return str(out).strip()


def _release_lock(
    session: Session, *, thread_id: UUID, account_id: UUID
) -> None:
    """Libère le lock optimiste (rare path d'échec LLM)."""
    try:
        session.execute(
            text(
                """
                UPDATE chat_thread
                   SET last_compacted_at = NULL
                 WHERE id = CAST(:tid AS UUID)
                   AND account_id = CAST(:aid AS UUID)
                """
            ),
            {"tid": str(thread_id), "aid": str(account_id)},
        )
    except Exception:  # pragma: no cover
        pass


def _write_audit_compaction(
    session: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    user_id: UUID | None,
    batch_size: int,
    new_summary_chars: int,
) -> UUID:
    """Audit log 'compact' (P3 append-only)."""
    audit_id = uuid4()
    session.execute(
        text(
            """
            INSERT INTO audit_log
                (id, user_id, account_id, entity_type, entity_id,
                 field, old_value, new_value, source_of_change,
                 "timestamp", created_at, updated_at, version)
            VALUES
                (CAST(:id AS UUID), CAST(:uid AS UUID), CAST(:aid AS UUID),
                 'ChatThread', CAST(:tid AS UUID),
                 'summary', CAST(:old AS JSONB), CAST(:new AS JSONB),
                 CAST('memory_system' AS source_of_change_t),
                 now(), now(), now(), 1)
            """
        ),
        {
            "id": str(audit_id),
            "uid": str(user_id) if user_id else None,
            "aid": str(account_id),
            "tid": str(thread_id),
            "old": json.dumps({"compacted_messages": int(batch_size)}),
            "new": json.dumps(
                {"action": "compact", "summary_chars": int(new_summary_chars)}
            ),
        },
    )
    return audit_id


def compact_thread(
    *,
    thread_id: UUID,
    account_id: UUID,
    user_id: UUID | None = None,
) -> int:
    """Compaction synchrone d'un thread (US6).

    Retourne le nombre de messages compactés (0 si rien à faire ou si lock
    non acquis).
    """
    settings = get_settings()
    batch_size = int(settings.LLM_AGENT_COMPACT_BATCH_SIZE)
    max_tokens = int(settings.LLM_AGENT_COMPACT_MAX_TOKENS)
    try:
        from app.db import SessionLocal
    except Exception as exc:  # pragma: no cover
        logger.warning("compactor: db import failed: %s", exc)
        return 0

    session: Session = SessionLocal()
    try:
        _set_rls_context(session, account_id=account_id)
        if not _try_acquire_lock(
            session, thread_id=thread_id, account_id=account_id
        ):
            session.rollback()
            return 0
        # Lock acquis — on commit immédiatement pour le rendre visible.
        session.commit()

        ids = _select_batch_message_ids(
            session,
            thread_id=thread_id,
            account_id=account_id,
            batch_size=batch_size,
        )
        if not ids:
            return 0
        msgs = _fetch_messages_for_summary(session, message_ids=ids)
        summary = _llm_summarize_messages(msgs=msgs, max_tokens=max_tokens)
        if not summary:
            _release_lock(
                session, thread_id=thread_id, account_id=account_id
            )
            session.commit()
            return 0
        try:
            session.execute(
                text(
                    """
                    UPDATE chat_thread
                       SET summary = :s, last_compacted_at = now()
                     WHERE id = CAST(:tid AS UUID)
                       AND account_id = CAST(:aid AS UUID)
                    """
                ),
                {"s": summary, "tid": str(thread_id), "aid": str(account_id)},
            )
            session.execute(
                text(
                    """
                    UPDATE chat_message SET compacted = TRUE
                    WHERE id = ANY(CAST(:ids AS UUID[]))
                      AND thread_id = CAST(:tid AS UUID)
                      AND account_id = CAST(:aid AS UUID)
                    """
                ),
                {
                    "ids": ids,
                    "tid": str(thread_id),
                    "aid": str(account_id),
                },
            )
            _write_audit_compaction(
                session,
                thread_id=thread_id,
                account_id=account_id,
                user_id=user_id,
                batch_size=len(ids),
                new_summary_chars=len(summary),
            )
            session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("compactor: write failed: %s", exc)
            session.rollback()
            return 0
        return len(ids)
    finally:
        try:
            session.close()
        except Exception:  # pragma: no cover
            pass


__all__ = ["compact_thread"]
