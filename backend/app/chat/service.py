"""F13 — Service layer (lazy thread create, archive guard, audit emission)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.chat import repository as repo
from app.chat.schemas import ContextJson

logger = logging.getLogger(__name__)


class ThreadArchivedError(Exception):
    """Tentative d'envoi sur un thread archivé (FR-021 → 409)."""


class ThreadNotFoundError(Exception):
    """Thread inconnu ou cross-tenant (FR-009 → 404)."""


def _default_title(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return f"Conversation du {now.strftime('%d/%m/%Y')}"


def ensure_active_thread(
    db: Session, *, account_id: UUID, user_id: UUID
) -> dict[str, Any]:
    """Renvoie le dernier thread actif, en crée un sinon (FR-023)."""
    threads = repo.list_threads(db, account_id=account_id, user_id=user_id, limit=1)
    if threads:
        return threads[0]
    return create_thread(db, account_id=account_id, user_id=user_id)


def create_thread(
    db: Session, *, account_id: UUID, user_id: UUID, title: str | None = None
) -> dict[str, Any]:
    title = title or _default_title()
    row = repo.create_thread(db, account_id=account_id, user_id=user_id, title=title)
    record_audit(
        db,
        entity_type="chat_thread",
        entity_id=row["id"],
        field="archived",
        old=None,
        new=False,
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )
    return row


def archive_thread(
    db: Session, *, thread_id: UUID, account_id: UUID, user_id: UUID
) -> None:
    thread = repo.get_thread_by_id(db, thread_id=thread_id, account_id=account_id)
    if not thread:
        raise ThreadNotFoundError(str(thread_id))
    ok = repo.archive_thread(db, thread_id=thread_id, account_id=account_id)
    if not ok:
        # déjà archivé : 204 idempotent côté API ; pas d'audit doublon
        return
    record_audit(
        db,
        entity_type="chat_thread",
        entity_id=thread_id,
        field="archived",
        old=False,
        new=True,
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )


def persist_user_turn(
    db: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    user_id: UUID,
    content: str,
    payload_json: dict[str, Any] | None,
    context_json: ContextJson | dict[str, Any],
) -> UUID:
    """Vérifie l'archive, insère le message user, audit, touch updated_at."""
    thread = repo.get_thread_by_id(db, thread_id=thread_id, account_id=account_id)
    if not thread:
        raise ThreadNotFoundError(str(thread_id))
    if thread["archived"]:
        raise ThreadArchivedError(str(thread_id))

    ctx_dict = (
        context_json.model_dump(exclude_none=False)
        if isinstance(context_json, ContextJson)
        else dict(context_json)
    )
    msg_id = repo.insert_message(
        db,
        thread_id=thread_id,
        account_id=account_id,
        user_id=user_id,
        role="user",
        content=content,
        payload_json=payload_json,
        context_json=ctx_dict,
    )
    repo.touch_thread(db, thread_id=thread_id)
    record_audit(
        db,
        entity_type="chat_message",
        entity_id=msg_id,
        field="role",
        old=None,
        new="user",
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )
    return msg_id


def persist_assistant_turn(
    db: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    user_id: UUID,
    content: str,
    payload_json: dict[str, Any] | None = None,
) -> UUID:
    """Insère le message assistant final consolidé. Audit source=llm."""
    msg_id = repo.insert_message(
        db,
        thread_id=thread_id,
        account_id=account_id,
        user_id=None,
        role="assistant",
        content=content,
        payload_json=payload_json,
        context_json=None,
    )
    repo.touch_thread(db, thread_id=thread_id)
    record_audit(
        db,
        entity_type="chat_message",
        entity_id=msg_id,
        field="role",
        old=None,
        new="assistant",
        source_of_change=SourceOfChange.LLM,
        user_id=user_id,
        account_id=account_id,
    )
    return msg_id
