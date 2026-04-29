"""F13 — CRUD threads + messages (SQLAlchemy parametrized)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_threads(db: Session, *, account_id: UUID, user_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT id, title, archived, created_at, updated_at
            FROM chat_thread
            WHERE account_id = :aid AND (user_id = :uid OR user_id IS NULL)
              AND archived = FALSE AND deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT :limit
            """
        ),
        {"aid": str(account_id), "uid": str(user_id), "limit": int(limit)},
    ).mappings().all()
    return [dict(r) for r in rows]


def create_thread(
    db: Session, *, account_id: UUID, user_id: UUID, title: str
) -> dict[str, Any]:
    new_id = uuid4()
    db.execute(
        text(
            """
            INSERT INTO chat_thread (id, account_id, user_id, title, archived)
            VALUES (:id, :aid, :uid, :title, FALSE)
            """
        ),
        {"id": str(new_id), "aid": str(account_id), "uid": str(user_id), "title": title},
    )
    row = db.execute(
        text(
            "SELECT id, title, archived, created_at, updated_at FROM chat_thread WHERE id = :id"
        ),
        {"id": str(new_id)},
    ).mappings().first()
    return dict(row) if row else {"id": new_id, "title": title}


def get_thread_by_id(
    db: Session, *, thread_id: UUID, account_id: UUID
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, account_id, user_id, title, archived, created_at, updated_at
            FROM chat_thread WHERE id = :id AND account_id = :aid AND deleted_at IS NULL
            """
        ),
        {"id": str(thread_id), "aid": str(account_id)},
    ).mappings().first()
    return dict(row) if row else None


def archive_thread(db: Session, *, thread_id: UUID, account_id: UUID) -> bool:
    res = db.execute(
        text(
            """
            UPDATE chat_thread
               SET archived = TRUE, updated_at = now(), version = version + 1
             WHERE id = :id AND account_id = :aid AND archived = FALSE
            """
        ),
        {"id": str(thread_id), "aid": str(account_id)},
    )
    return (res.rowcount or 0) > 0


def touch_thread(db: Session, *, thread_id: UUID) -> None:
    db.execute(
        text("UPDATE chat_thread SET updated_at = now() WHERE id = :id"),
        {"id": str(thread_id)},
    )


def insert_message(
    db: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    user_id: UUID | None,
    role: str,
    content: str,
    payload_json: dict[str, Any] | None = None,
    context_json: dict[str, Any] | None = None,
) -> UUID:
    msg_id = uuid4()
    db.execute(
        text(
            """
            INSERT INTO chat_message
              (id, account_id, user_id, role, content, payload_json, context_json, thread_id)
            VALUES
              (:id, :aid, :uid, :role, :content,
               CAST(:payload AS JSONB), CAST(:ctx AS JSONB), :tid)
            """
        ),
        {
            "id": str(msg_id),
            "aid": str(account_id),
            "uid": str(user_id) if user_id else None,
            "role": role,
            "content": content,
            "payload": _to_json(payload_json),
            "ctx": _to_json(context_json),
            "tid": str(thread_id),
        },
    )
    return msg_id


def list_messages(
    db: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    after_id: UUID | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    base = """
        SELECT id, thread_id, role, content, payload_json, context_json, created_at
        FROM chat_message
        WHERE thread_id = :tid AND account_id = :aid
          AND role <> 'system'
          AND deleted_at IS NULL
    """
    params: dict[str, Any] = {
        "tid": str(thread_id),
        "aid": str(account_id),
        "limit": int(limit),
    }
    if after_id is not None:
        base += " AND created_at > (SELECT created_at FROM chat_message WHERE id = :aid_after)"
        params["aid_after"] = str(after_id)
    base += " ORDER BY created_at ASC LIMIT :limit"
    rows = db.execute(text(base), params).mappings().all()
    return [dict(r) for r in rows]


def update_message_embedding(
    db: Session, *, message_id: UUID, embedding: list[float]
) -> None:
    db.execute(
        text("UPDATE chat_message SET embedding = :emb WHERE id = :id"),
        {"id": str(message_id), "emb": embedding},
    )


def _to_json(v: Any) -> str | None:
    if v is None:
        return None
    import json as _json

    return _json.dumps(v, default=str)
