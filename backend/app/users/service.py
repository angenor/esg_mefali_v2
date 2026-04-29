"""F02 — Service utilisateurs."""

from __future__ import annotations

from app.auth.schemas import MeOut
from app.models.account_user import AccountUser


def get_me(user: AccountUser) -> MeOut:
    return MeOut(
        user_id=user.id,
        account_id=user.account_id,
        role=str(user.role),  # type: ignore[arg-type]
        email=user.email,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )
