"""F05 T033 — Privacy & consent endpoints.

Endpoints (PME-scoped, RLS-isolated):
- ``GET  /me/consentements`` -> list of ConsentOut
- ``POST /me/consentements/{kind}`` -> updated ConsentOut

The implementation deliberately stays narrow: only the consent surface is
shipped here. Data summary / export / deletion endpoints (US1) are deferred.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser
from app.schemas.consent import ConsentKind, ConsentOut, ConsentToggleIn
from app.services import consent_service

router = APIRouter(prefix="/me/consentements", tags=["privacy"])


@router.get("", response_model=list[ConsentOut])
def list_my_consents(
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> list[ConsentOut]:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "PME sans account_id."},
        )
    rows = consent_service.list_for_account(db, user.account_id)
    return [ConsentOut(**r) for r in rows]


@router.post("/{kind}", response_model=ConsentOut)
def toggle_my_consent(
    kind: ConsentKind,
    body: ConsentToggleIn,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> ConsentOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "PME sans account_id."},
        )
    row = consent_service.toggle(
        db,
        account_id=user.account_id,
        kind=kind,
        given=body.given,
        source_of_change="manual",
        user_id=user.id,
    )
    db.commit()
    return ConsentOut(**row)
