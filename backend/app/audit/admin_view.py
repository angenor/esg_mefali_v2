"""F10 — ``audit_admin_view`` helper.

Wraps :func:`app.audit.helper.record_audit` for admin read-only consultations.
Each ``GET /admin/pme/{id}?section=X`` produces one ``audit_log`` row with
``source_of_change='admin'``, ``entity_type='admin_view'`` and a constrained
``section`` (enum 7 values).

Strategy : **fail-closed** — if the audit insert fails, the caller MUST raise
HTTP 503 to ensure no admin consultation is served without trace (US2).
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange


class AdminViewSection(StrEnum):
    """7 sections strictement autorisées (cf. spec.md FR-002)."""

    OVERVIEW = "overview"
    ENTREPRISE = "entreprise"
    PROJETS = "projets"
    CANDIDATURES = "candidatures"
    SCORES = "scores"
    ATTESTATIONS = "attestations"
    AUDIT = "audit"


def audit_admin_view(
    db: Session,
    *,
    account_id: UUID | str,
    section: AdminViewSection | str,
    request: Request | None = None,
    admin_user_id: UUID | str | None = None,
) -> UUID:
    """Insert an ``admin_view`` audit row.

    Returns the new row id. Raises if the insertion fails (fail-closed).
    """
    sec = (
        section.value
        if isinstance(section, AdminViewSection)
        else AdminViewSection(str(section)).value
    )

    request_id = None
    if request is not None:
        request_id = getattr(request.state, "request_id", None)

    row_id = record_audit(
        db,
        entity_type="admin_view",
        entity_id=account_id,
        field=f"section.{sec}",
        old=None,
        new={"section": sec},
        source_of_change=SourceOfChange.ADMIN,
        notes=f"admin viewed section={sec}",
        user_id=admin_user_id,
        account_id=account_id,
        request_id=request_id,
        # IP intentionally omitted (US2: no admin PII in PME-visible projection).
        ip=None,
    )
    if row_id is None:
        raise RuntimeError("audit_admin_view: insert returned None (fail-closed)")
    return row_id
