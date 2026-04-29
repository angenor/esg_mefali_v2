"""F04 — Versioning publish endpoints (US4 + US5).

POST /api/v1/{table}/{logical_id}/publish — admin-only, requires If-Match
header carrying the current integer ``version`` of the active row.
Returns 412 with ``{"error":"version_conflict","current_version":<n>}`` on stale
If-Match (OptimisticLockError).
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.models.account_user import AccountUser
from app.versioning.exceptions import OptimisticLockError
from app.versioning.helpers import publish_new_version

router = APIRouter(prefix="/api/v1", tags=["versioning"])


PUBLISHABLE_TABLES = {
    "referentiels": "referentiel",
    "indicateurs": "indicateur",
    "criteres": "critere",
    "formules": "formule",
    "seuils": "seuil",
    "facteurs-emission": "facteur_emission",
    "templates": "template",
}


def _parse_if_match(if_match: str | None) -> int:
    if not if_match:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={"error": "if_match_required"},
        )
    cleaned = if_match.strip().strip('"').strip("'")
    try:
        return int(cleaned)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "if_match_invalid"},
        ) from exc


@router.post("/{table}/{logical_id}/publish")
def publish_route(
    table: str,
    logical_id: UUID,
    payload: Annotated[dict[str, Any], Body(...)],
    admin: Annotated[AccountUser, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> dict[str, Any]:
    """Publish a new version of a versioned catalogue row."""
    if table not in PUBLISHABLE_TABLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "unknown_versioned_table"},
        )
    version_at_load = _parse_if_match(if_match)
    real_table = PUBLISHABLE_TABLES[table]

    try:
        new_row = publish_new_version(
            db,
            table=real_table,
            logical_id=logical_id,
            new_payload=payload,
            version_at_load=version_at_load,
        )
    except OptimisticLockError as exc:
        # HTTP 412 Precondition Failed
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "error": "version_conflict",
                "current_version": exc.current_version,
            },
        ) from exc

    # Journal the publish event (T074).
    record_audit(
        db,
        entity_type=real_table,
        entity_id=new_row["id"],
        field="version",
        old=version_at_load,
        new=new_row.get("version_num") or new_row.get("version"),
        source_of_change=SourceOfChange.ADMIN,
        user_id=str(admin.id),
        account_id=str(admin.account_id) if admin.account_id else None,
    )
    db.commit()
    return {
        "id": str(new_row["id"]),
        "logical_id": str(new_row["logical_id"]),
        "version": new_row.get("version_num") or new_row.get("version"),
        "valid_from": new_row["valid_from"].isoformat() if new_row.get("valid_from") else None,
    }
