"""F34 — Routes PME ``/me/notifications`` (étendu F52 US1)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser
from app.notifications.preferences_service import (
    get_preferences,
    update_preferences,
)
from app.notifications.schemas import NotificationOut, NotificationReadOut
from app.notifications.schemas_f52 import ReadAllRequest, ReadAllResponse
from app.notifications.service import (
    NotificationNotFoundError,
    NotificationService,
)
from app.users.schemas_f52 import (
    NotificationPreferencesOut,
    NotificationPreferencesUpdate,
)

router = APIRouter(prefix="/me/notifications", tags=["notifications"])
preferences_router = APIRouter(
    prefix="/me/notification-preferences", tags=["notifications"]
)


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


@router.post("/read-all", response_model=ReadAllResponse)
def mark_all_read(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    body: Annotated[ReadAllRequest, Body()] = ReadAllRequest(),
) -> ReadAllResponse:
    """F52 SC-002 — bulk mark-all-read avec filtre optionnel ``kinds``."""
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME requis."},
        )
    updated, remaining = NotificationService.mark_all_read(
        db,
        account_id=user.account_id,
        user_id=user.id,
        kinds=body.kinds,
    )
    db.commit()
    return ReadAllResponse(
        updated_count=updated, unread_count_after=remaining
    )


# ---------------------------------------------------------------------------
# F52 US2 — Préférences (matrice kind × channel)
# ---------------------------------------------------------------------------


@preferences_router.get("", response_model=NotificationPreferencesOut)
def list_notification_preferences(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationPreferencesOut:
    out = get_preferences(db, user=user)
    db.commit()
    return out


@preferences_router.patch("", response_model=NotificationPreferencesOut)
def patch_notification_preferences(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    body: Annotated[NotificationPreferencesUpdate, Body()],
) -> NotificationPreferencesOut:
    out = update_preferences(db, user=user, updates=list(body.updates))
    db.commit()
    return out
