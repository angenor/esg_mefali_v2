"""F02 — Router /me."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.schemas import MeOut
from app.models.account_user import AccountUser
from app.users.service import get_me

router = APIRouter(tags=["users"])


@router.get("/me", response_model=MeOut)
def me(user: AccountUser = Depends(get_current_user)) -> MeOut:
    return get_me(user)
