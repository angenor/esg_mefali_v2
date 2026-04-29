"""F05 T031 — Consent service: list, query, toggle.

The service stays thin: it manipulates rows on ``consent`` (RLS-scoped to
the current account) and emits an audit_log entry on each toggle via
``app.audit.helper.record_audit`` (F04).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.schemas.consent import ConsentKind


def list_for_account(db: Session, account_id: uuid.UUID) -> list[dict]:
    """Return all consent rows for an account as dicts (RLS-scoped)."""
    rows = db.execute(
        text(
            """
            SELECT id, account_id, consent_kind, given, given_at, withdrawn_at,
                   source_of_change, updated_at
            FROM consent
            WHERE account_id = :aid
            ORDER BY consent_kind
            """
        ),
        {"aid": str(account_id)},
    ).mappings().all()
    return [dict(r) for r in rows]


def is_active(db: Session, account_id: uuid.UUID, kind: ConsentKind | str) -> bool:
    """Return True if the named consent is currently ``given=true``."""
    k = kind.value if isinstance(kind, ConsentKind) else str(kind)
    val = db.execute(
        text(
            "SELECT given FROM consent WHERE account_id = :aid AND consent_kind = :k"
        ),
        {"aid": str(account_id), "k": k},
    ).scalar()
    return bool(val)


def toggle(
    db: Session,
    *,
    account_id: uuid.UUID,
    kind: ConsentKind | str,
    given: bool,
    source_of_change: str = "manual",
    user_id: uuid.UUID | None = None,
) -> dict:
    """Upsert the consent row, audit the change, return the new row.

    The previous value (if any) is included in the audit entry's
    ``old_value`` so reviewers can reconstruct toggle history.
    """
    k = kind.value if isinstance(kind, ConsentKind) else str(kind)
    now = datetime.now(UTC)

    prev = db.execute(
        text("SELECT given FROM consent WHERE account_id = :aid AND consent_kind = :k"),
        {"aid": str(account_id), "k": k},
    ).scalar()

    db.execute(
        text(
            """
            INSERT INTO consent (account_id, consent_kind, given, given_at,
                                 withdrawn_at, source_of_change)
            VALUES (:aid, :k, :given,
                    CASE WHEN :given THEN :now ELSE NULL END,
                    CASE WHEN :given THEN NULL ELSE :now END,
                    :src)
            ON CONFLICT (account_id, consent_kind) DO UPDATE SET
                given = EXCLUDED.given,
                given_at = CASE WHEN EXCLUDED.given THEN :now ELSE consent.given_at END,
                withdrawn_at = CASE WHEN EXCLUDED.given THEN consent.withdrawn_at ELSE :now END,
                source_of_change = EXCLUDED.source_of_change
            """
        ),
        {"aid": str(account_id), "k": k, "given": given, "now": now, "src": source_of_change},
    )

    # Audit (F04). ``field='consent_kind'`` + new_value=k follows the schema.
    record_audit(
        db,
        entity_type="consent",
        entity_id=account_id,
        field="consent_kind",
        old={"kind": k, "given": bool(prev) if prev is not None else None},
        new={"kind": k, "given": given},
        source_of_change=SourceOfChange(source_of_change)
        if source_of_change in {s.value for s in SourceOfChange}
        else SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )

    row = db.execute(
        text(
            """
            SELECT id, account_id, consent_kind, given, given_at, withdrawn_at,
                   source_of_change, updated_at
            FROM consent WHERE account_id = :aid AND consent_kind = :k
            """
        ),
        {"aid": str(account_id), "k": k},
    ).mappings().one()
    return dict(row)
