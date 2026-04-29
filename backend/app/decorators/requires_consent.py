"""F05 T032 — ``RequiresConsent`` FastAPI dependency.

Usage::

    from app.decorators.requires_consent import RequiresConsent
    from app.schemas.consent import ConsentKind

    @router.post("/me/mobile-money/transfer")
    def transfer(
        _: None = Depends(RequiresConsent(ConsentKind.MOBILE_MONEY)),
        ...
    ):
        ...

If the consent is missing or ``given=false``, raises ``HTTPException(403)``
with body ``{"error":"consent_required","kind":<kind>}``.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser
from app.schemas.consent import ConsentKind
from app.services import consent_service


class RequiresConsent:
    """Dependency callable enforcing a granular consent gate."""

    def __init__(self, kind: ConsentKind) -> None:
        self.kind = kind

    def __call__(
        self,
        user: AccountUser = Depends(get_current_pme),
        db: Session = Depends(get_db),
    ) -> None:
        if user.account_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "consent_required", "kind": self.kind.value},
            )
        if not consent_service.is_active(db, user.account_id, self.kind):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "consent_required", "kind": self.kind.value},
            )
