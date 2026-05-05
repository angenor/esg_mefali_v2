"""F02 + F42 — Router /me et /me/preferences."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import MeOut
from app.db import get_db
from app.models.account_user import AccountUser
from app.users.schemas import UserPreferencesOut, UserPreferencesPatch
from app.users.service import (
    get_me,
    get_or_create_preferences,
    update_preferences,
)

router = APIRouter(tags=["users"])


@router.get("/me", response_model=MeOut)
def me(user: AccountUser = Depends(get_current_user)) -> MeOut:
    return get_me(user)


@router.get("/me/preferences", response_model=UserPreferencesOut)
def get_preferences(
    user: AccountUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferencesOut:
    prefs = get_or_create_preferences(db, user)
    # Capture les valeurs AVANT le commit : SET LOCAL est purgé après commit
    # et un refresh via RLS échouerait (current_account_id vide).
    out = UserPreferencesOut(
        onboarding_state=prefs.onboarding_state,  # type: ignore[arg-type]
        onboarding_state_updated_at=prefs.onboarding_state_updated_at,
    )
    db.commit()
    return out


@router.patch("/me/preferences", response_model=UserPreferencesOut)
def patch_preferences(
    body: Annotated[UserPreferencesPatch, Body()],
    user: AccountUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferencesOut:
    prefs = update_preferences(db, user, body)
    out = UserPreferencesOut(
        onboarding_state=prefs.onboarding_state,  # type: ignore[arg-type]
        onboarding_state_updated_at=prefs.onboarding_state_updated_at,
    )
    db.commit()
    return out
