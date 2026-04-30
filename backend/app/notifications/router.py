"""F34 — Routes PME ``/me/notifications``."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser
from app.notifications.schemas import NotificationOut, NotificationReadOut
from app.notifications.service import (
    NotificationNotFoundError,
    NotificationService,
)

router = APIRouter(prefix="/me/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    unread: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NotificationOut]:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME requis."},
        )
    items = NotificationService.list_for_account(
        db,
        account_id=user.account_id,
        unread=unread,
        limit=limit,
        offset=offset,
    )
    return [NotificationOut.model_validate(it) for it in items]


@router.patch("/{notification_id}/read", response_model=NotificationReadOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationReadOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME requis."},
        )
    try:
        notif = NotificationService.mark_read(
            db,
            notification_id=notification_id,
            account_id=user.account_id,
            user_id=user.id,
        )
    except NotificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "notification_not_found"},
        ) from exc
    db.commit()
    db.refresh(notif)
    assert notif.read_at is not None
    return NotificationReadOut(id=notif.id, read_at=notif.read_at)
