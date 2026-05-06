"""F57 — Routes ``/me/chat/threads/{thread_id}/memory`` (US3 + US4).

- ``GET``  → ``MemorySnapshotV2`` (FR-007).
- ``DELETE`` → ``ForgetMemoryResult`` (FR-008, RGPD synchrone).

Cross-tenant ⇒ 404 (P2). RLS GUC positionnée par middleware F02.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.chat.memory.schemas import ForgetMemoryResult, MemorySnapshotV2
from app.chat.memory.service import (
    ThreadMemoryNotFoundError,
    forget_thread_memory,
    get_memory_snapshot,
)
from app.db import get_db
from app.models.account_user import AccountUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/chat", tags=["chat", "memory"])


@router.get(
    "/threads/{thread_id}/memory",
    response_model=MemorySnapshotV2,
    status_code=status.HTTP_200_OK,
)
def get_memory(
    thread_id: UUID,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    """Retourne le snapshot mémoire enrichi du thread (US3)."""
    try:
        return get_memory_snapshot(
            db, thread_id=thread_id, account_id=user.account_id
        )
    except ThreadMemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="thread_not_found"
        ) from exc


@router.delete(
    "/threads/{thread_id}/memory",
    response_model=ForgetMemoryResult,
    status_code=status.HTTP_200_OK,
)
def forget_memory(
    thread_id: UUID,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    """Forget RGPD synchrone (US4). Idempotent."""
    try:
        result = forget_thread_memory(
            db,
            thread_id=thread_id,
            account_id=user.account_id,
            user_id=user.id,
        )
    except ThreadMemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="thread_not_found"
        ) from exc
    db.commit()
    return result


__all__ = ["forget_memory", "get_memory", "router"]
