"""F29 - FastAPI router pour endpoints credit scoring."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.credit import service as credit_service
from app.credit.csv_parser import (
    StatementParseError,
    StatementTooLargeError,
)
from app.credit.schemas import (
    CreditDataIn,
    CreditDataKind,
    CreditDataOut,
    CreditRecommendationsOut,
    CreditScoreOut,
    EligibilityListOut,
    MethodologyOut,
    ScoreHistoryOut,
)
from app.db import get_db
from app.decorators.requires_consent import RequiresConsent
from app.models.account_user import AccountUser
from app.schemas.consent import ConsentKind

router = APIRouter(tags=["credit"])
public_router = APIRouter(tags=["credit-public"])


def _account_uuid(user: AccountUser) -> UUID:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME non rattache."},
        )
    aid = user.account_id
    return aid if isinstance(aid, UUID) else UUID(str(aid))


def _user_uuid(user: AccountUser) -> UUID | None:
    uid = getattr(user, "id", None)
    if uid is None:
        return None
    return uid if isinstance(uid, UUID) else UUID(str(uid))


def _resolve_entreprise_id(
    user: AccountUser, override: UUID | None = None
) -> UUID:
    if override is not None:
        return override
    eid = getattr(user, "entreprise_id", None)
    if eid is not None:
        return eid if isinstance(eid, UUID) else UUID(str(eid))
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "entreprise_required",
            "message": "Entreprise non rattachee au compte.",
        },
    )


@router.post("/me/credit-data", response_model=CreditDataOut)
def post_credit_data(
    body: CreditDataIn,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    entreprise_id: UUID | None = None,
) -> CreditDataOut:
    if body.kind == CreditDataKind.PHOTOS:
        RequiresConsent(ConsentKind.EXPLOITATION_PHOTOS)(user, db)
    if body.kind == CreditDataKind.MOBILE_MONEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "use_mobile_money_endpoint",
                "message": "Utiliser POST /me/credit-data/mobile-money pour les "
                "statements Mobile Money (parsing CSV).",
            },
        )
    eid = _resolve_entreprise_id(user, entreprise_id)
    result = credit_service.submit_credit_data(
        db,
        account_id=_account_uuid(user),
        entreprise_id=eid,
        user_id=_user_uuid(user),
        kind=body.kind,
        payload=body.payload,
        valid_until=body.valid_until,
    )
    return CreditDataOut(**result)


@router.post(
    "/me/credit-data/mobile-money",
    response_model=CreditDataOut,
    dependencies=[Depends(RequiresConsent(ConsentKind.MOBILE_MONEY))],
)
async def post_mobile_money(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    statement: Annotated[UploadFile, File(...)],
    entreprise_id: UUID | None = None,
) -> CreditDataOut:
    raw = await statement.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_file", "message": "Fichier vide."},
        )
    eid = _resolve_entreprise_id(user, entreprise_id)
    try:
        result = credit_service.submit_mobile_money_csv(
            db,
            account_id=_account_uuid(user),
            entreprise_id=eid,
            user_id=_user_uuid(user),
            raw_bytes=raw,
        )
    except StatementTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "statement_too_large", "message": str(exc)},
        ) from exc
    except StatementParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "statement_invalid", "message": str(exc)},
        ) from exc
    return CreditDataOut(**result)


@router.post("/me/credit-score/recompute", response_model=CreditScoreOut)
def post_recompute(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    entreprise_id: UUID | None = None,
) -> CreditScoreOut:
    eid = _resolve_entreprise_id(user, entreprise_id)
    result = credit_service.recompute_score(
        db,
        account_id=_account_uuid(user),
        entreprise_id=eid,
        user_id=_user_uuid(user),
    )
    return CreditScoreOut(**result)


@router.get("/me/credit-score", response_model=CreditScoreOut)
def get_credit_score(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    entreprise_id: UUID | None = None,
) -> CreditScoreOut:
    eid = _resolve_entreprise_id(user, entreprise_id)
    try:
        result = credit_service.get_latest_score(
            db,
            account_id=_account_uuid(user),
            entreprise_id=eid,
        )
    except credit_service.CreditScoreNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "credit_score_not_found", "message": str(exc)},
        ) from exc
    return CreditScoreOut(**result)


@router.get("/me/credit-score/history", response_model=ScoreHistoryOut)
def get_credit_score_history(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=6, ge=1, le=24),
    entreprise_id: UUID | None = None,
) -> ScoreHistoryOut:
    eid = _resolve_entreprise_id(user, entreprise_id)
    items = credit_service.list_history(
        db,
        account_id=_account_uuid(user),
        entreprise_id=eid,
        limit=limit,
    )
    return ScoreHistoryOut(items=items)


@router.get("/me/credit-score/eligibility", response_model=EligibilityListOut)
def get_credit_score_eligibility(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    entreprise_id: UUID | None = None,
) -> EligibilityListOut:
    eid = _resolve_entreprise_id(user, entreprise_id)
    result = credit_service.evaluate_eligibility(
        db,
        account_id=_account_uuid(user),
        entreprise_id=eid,
    )
    return EligibilityListOut(**result)


@router.get(
    "/me/credit-score/recommendations",
    response_model=CreditRecommendationsOut,
)
def get_credit_score_recommendations(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=5, ge=1, le=5),
    entreprise_id: UUID | None = None,
) -> CreditRecommendationsOut:
    eid = _resolve_entreprise_id(user, entreprise_id)
    result = credit_service.list_recommendations(
        db,
        account_id=_account_uuid(user),
        entreprise_id=eid,
        limit=limit,
    )
    return CreditRecommendationsOut(**result)


@public_router.get("/methodologie/credit-scoring", response_model=MethodologyOut)
def get_methodology_public(
    db: Annotated[Session, Depends(get_db)],
    version: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    try:
        return credit_service.get_methodology(db, version=version)
    except credit_service.MethodologyNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "methodology_not_found", "message": str(exc)},
        ) from exc
