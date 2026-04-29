"""F10 US1 — Read-only PME view service.

MVP scope: aggregates the *available* tables (``account`` + ``account_user``).
Sections like projets/candidatures/scores/attestations are still empty in this
slice (their tables are introduced by F11/F12/F23/F30) and resolve to empty
lists — the section enum and the audit trail are already wired so the
contract is stable when those features land.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.admin_view import AdminViewSection, audit_admin_view


@dataclass(frozen=True)
class PmeListItem:
    account_id: UUID
    name: str
    primary_email: str | None
    user_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": str(self.account_id),
            "name": self.name,
            "primary_email": self.primary_email,
            "user_count": self.user_count,
        }


def list_accounts(
    db: Session, *, q: str | None = None, limit: int = 25, offset: int = 0
) -> dict[str, Any]:
    """Paginated list of PME accounts (admins excluded)."""
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    where = ""
    if q:
        where = (
            " WHERE (a.name ILIKE :q OR EXISTS ("
            "  SELECT 1 FROM account_user u2 WHERE u2.account_id = a.id"
            "  AND u2.email ILIKE :q AND u2.role = 'pme'))"
        )
        params["q"] = f"%{q}%"

    sql = text(
        "SELECT a.id, a.name, "
        "(SELECT email FROM account_user u WHERE u.account_id = a.id "
        " AND u.role='pme' AND u.deleted_at IS NULL "
        " ORDER BY u.created_at LIMIT 1) AS primary_email, "
        "(SELECT count(*) FROM account_user u WHERE u.account_id = a.id "
        " AND u.role='pme' AND u.deleted_at IS NULL) AS user_count "
        "FROM account a"
        f"{where} "
        "ORDER BY a.created_at DESC "
        "LIMIT :limit OFFSET :offset"
    )
    rows = db.execute(sql, params).all()
    items = [
        PmeListItem(
            account_id=r.id,
            name=r.name,
            primary_email=r.primary_email,
            user_count=int(r.user_count or 0),
        ).to_dict()
        for r in rows
    ]

    count_sql = text("SELECT count(*) FROM account a" + where)
    total = db.execute(count_sql, {k: v for k, v in params.items() if k == "q"}).scalar() or 0

    return {
        "items": items,
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


def get_account_detail(
    db: Session,
    *,
    account_id: UUID,
    section: AdminViewSection,
    request: Request | None,
    admin_user_id: UUID | str | None,
) -> dict[str, Any]:
    """Return the read-only detail for one PME account.

    Always emits an ``admin_view`` audit row (fail-closed). Missing source
    tables (projets/candidatures/...) resolve to empty arrays.
    """
    acc = db.execute(
        text("SELECT id, name, created_at FROM account WHERE id = :id"),
        {"id": str(account_id)},
    ).first()
    if acc is None:
        return {}  # caller maps to 404

    users = db.execute(
        text(
            "SELECT id, email, role, last_login_at, deleted_at "
            "FROM account_user WHERE account_id = :id ORDER BY created_at"
        ),
        {"id": str(account_id)},
    ).all()

    # Fail-closed audit BEFORE returning any payload.
    audit_admin_view(
        db,
        account_id=account_id,
        section=section,
        request=request,
        admin_user_id=admin_user_id,
    )
    db.commit()

    return {
        "account": {
            "id": str(acc.id),
            "name": acc.name,
            "created_at": acc.created_at.isoformat() if acc.created_at else None,
        },
        "section": section.value,
        "overview": {
            "user_count": len(users),
            "users": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "role": u.role,
                    "last_login_at": (
                        u.last_login_at.isoformat() if u.last_login_at else None
                    ),
                    "deleted": u.deleted_at is not None,
                }
                for u in users
            ],
        },
        # The following sections resolve to empty lists until F11/F12/F23/F30 land.
        "entreprise": None,
        "projets": [],
        "candidatures": [],
        "scores": [],
        "attestations": [],
        "audit": [],
    }
