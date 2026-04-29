"""F12 - Routes API /me/projets."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser
from app.projets import events as projet_events
from app.projets.schemas import (
    ConflictOut,
    ProjetCreate,
    ProjetListOut,
    ProjetPatch,
    ProjetRead,
    TransitionIn,
)
from app.projets.service import (
    DeleteProtected,
    ProjetNotFound,
    VersionConflict,
    aggregate_read,
    aggregate_summary,
    create_projet,
    delete_projet,
    duplicate_projet,
    get_projet,
    list_projets,
    patch_projet,
    transition_projet,
)
from app.projets.validators import ValidationError as ProjetValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/projets", tags=["projets"])


def _parse_if_match(header_value: str | None) -> int:
    if header_value is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "if_match_required",
                "message": "Header If-Match: <version> requis pour cette mutation.",
            },
        )
    try:
        v = int(header_value.strip().strip('"'))
        if v < 1:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "if_match_invalid", "message": "If-Match doit etre un entier positif."},
        ) from exc
    return v


@router.get("", response_model=ProjetListOut)
def list_endpoint(
    statut: str | None = Query(default=None),
    type_impact: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    rows, total = list_projets(
        db, account_id=user.account_id,
        statut=statut, type_impact=type_impact, page=page, limit=limit,
    )
    return {
        "items": [aggregate_summary(r) for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("", response_model=ProjetRead, status_code=status.HTTP_201_CREATED)
def create_endpoint(
    body: ProjetCreate,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_unset=True)
    try:
        row = create_projet(db, account_id=user.account_id, user_id=user.id, payload=payload)
    except ProjetValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    db.commit()
    return aggregate_read(row)


@router.get("/events")
async def stream_events(
    user: AccountUser = Depends(get_current_pme),
) -> StreamingResponse:
    account_id = str(user.account_id)

    async def gen():
        async for msg in projet_events.subscribe(account_id):
            if msg.startswith(":"):
                yield msg
            else:
                yield f"data: {msg}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/{projet_id}", response_model=ProjetRead)
def get_endpoint(
    projet_id: str,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    try:
        row = get_projet(db, projet_id=projet_id, account_id=user.account_id)
    except ProjetNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    return aggregate_read(row)


@router.patch("/{projet_id}", response_model=ProjetRead)
def patch_endpoint(
    projet_id: str,
    body: ProjetPatch,
    if_match: str | None = Header(default=None, alias="If-Match"),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    expected = _parse_if_match(if_match)
    payload = body.model_dump(exclude_unset=True)
    try:
        row = patch_projet(
            db,
            projet_id=projet_id,
            account_id=user.account_id,
            user_id=user.id,
            expected_version=expected,
            payload=payload,
        )
    except ProjetNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    except VersionConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictOut(
                message="Le projet a ete modifie par ailleurs.",
                current_version=exc.current_version,
                your_version=exc.your_version,
            ).model_dump(),
        ) from exc
    except ProjetValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    db.commit()
    return aggregate_read(row)


@router.post("/{projet_id}/duplicate", response_model=ProjetRead, status_code=201)
def duplicate_endpoint(
    projet_id: str,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    try:
        row = duplicate_projet(
            db, projet_id=projet_id, account_id=user.account_id, user_id=user.id,
        )
    except ProjetNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    db.commit()
    return aggregate_read(row)


@router.delete("/{projet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_endpoint(
    projet_id: str,
    x_confirm: str | None = Header(default=None, alias="X-Confirm"),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> None:
    confirm = (x_confirm or "").strip().lower() == "true"
    try:
        delete_projet(
            db,
            projet_id=projet_id,
            account_id=user.account_id,
            user_id=user.id,
            confirm=confirm,
        )
    except ProjetNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    except DeleteProtected as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "delete_protected",
                "message": str(exc),
                "statut": exc.statut,
            },
        ) from exc
    db.commit()


@router.post("/{projet_id}/transition", response_model=ProjetRead)
def transition_endpoint(
    projet_id: str,
    body: TransitionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    expected = _parse_if_match(if_match)
    try:
        row = transition_projet(
            db,
            projet_id=projet_id,
            account_id=user.account_id,
            user_id=user.id,
            expected_version=expected,
            to=body.to,
        )
    except ProjetNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    except VersionConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictOut(
                message="Le projet a ete modifie par ailleurs.",
                current_version=exc.current_version,
                your_version=exc.your_version,
            ).model_dump(),
        ) from exc
    db.commit()
    return aggregate_read(row)
