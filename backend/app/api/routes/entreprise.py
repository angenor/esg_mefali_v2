"""F11 — Routes API pour le profil entreprise PME (`/me/entreprise`)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.entreprise import events as entreprise_events
from app.entreprise.completeness import (
    compute_missing_per_feature,
    compute_percentage,
)
from app.entreprise.schemas import (
    CompletenessOut,
    ConflictOut,
    EntreprisePatchIn,
    EntreprisePutIn,
    EntrepriseRead,
    SectorOut,
)
from app.entreprise.service import (
    VersionConflict,
    aggregate_read,
    get_or_provision_entreprise,
    update_partial,
)
from app.entreprise.taxonomy import SECTORS
from app.models.account_user import AccountUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/entreprise", tags=["entreprise"])


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
            detail={
                "code": "if_match_invalid",
                "message": "If-Match doit être un entier positif.",
            },
        ) from exc
    return v


@router.get("", response_model=EntrepriseRead)
def get_entreprise(
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    row = get_or_provision_entreprise(db, account_id=user.account_id, user_id=user.id)
    db.commit()
    return aggregate_read(db, row)


@router.patch("", response_model=EntrepriseRead)
def patch_entreprise(
    body: EntreprisePatchIn,
    request: Request,  # noqa: ARG001
    if_match: str | None = Header(default=None, alias="If-Match"),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    expected_version = _parse_if_match(if_match)
    payload = body.model_dump(exclude_unset=True)
    try:
        row = update_partial(
            db,
            account_id=user.account_id,
            user_id=user.id,
            expected_version=expected_version,
            payload=payload,
        )
    except VersionConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictOut(
                message="Le profil a été modifié par ailleurs. Rechargez et recommencez.",
                current_version=exc.current_version,
                your_version=exc.your_version,
            ).model_dump(),
        ) from exc
    db.commit()
    return aggregate_read(db, row)


@router.put("", response_model=EntrepriseRead)
def put_entreprise(
    body: EntreprisePutIn,
    request: Request,  # noqa: ARG001
    if_match: str | None = Header(default=None, alias="If-Match"),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    expected_version = _parse_if_match(if_match)
    payload = body.model_dump(exclude_unset=True)
    try:
        row = update_partial(
            db,
            account_id=user.account_id,
            user_id=user.id,
            expected_version=expected_version,
            payload=payload,
        )
    except VersionConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictOut(
                message="Le profil a été modifié par ailleurs.",
                current_version=exc.current_version,
                your_version=exc.your_version,
            ).model_dump(),
        ) from exc
    db.commit()
    return aggregate_read(db, row)


@router.get("/sectors", response_model=list[SectorOut])
def list_sectors(_: AccountUser = Depends(get_current_pme)) -> Any:
    return [{"code": s.code, "label": s.label} for s in SECTORS]


@router.get("/completeness", response_model=CompletenessOut)
def get_completeness(
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    row = get_or_provision_entreprise(db, account_id=user.account_id, user_id=user.id)
    db.commit()
    profile = aggregate_read(db, row)
    pct = compute_percentage(profile)
    missing = compute_missing_per_feature(profile)
    return {
        "percentage": pct,
        "missing_required_for_features": missing,
    }


@router.get("/events")
async def stream_events(
    user: AccountUser = Depends(get_current_pme),
) -> StreamingResponse:
    account_id = str(user.account_id)

    async def gen():
        async for msg in entreprise_events.subscribe(account_id):
            if msg.startswith(":"):
                yield msg
            else:
                yield f"data: {msg}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
