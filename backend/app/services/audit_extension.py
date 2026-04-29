"""F05 T010 — Purge context manager for audit_log RTBF exception.

Module 0 invariant: audit_log is append-only EXCEPT inside this context,
where ONLY the ``user_id`` column may be UPDATEd. The trigger
``audit_log_immutable`` (migration 0005a) enforces the column-level rule.

Usage::

    with purge_context(db):
        db.execute(
            text("UPDATE audit_log SET user_id = :anon WHERE account_id = :aid"),
            {"anon": pseudonymize(account_id), "aid": str(account_id)},
        )

The setting is ``LOCAL`` to the current transaction; commit or rollback
resets it. Outside this block any UPDATE/DELETE on ``audit_log`` raises.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session


@contextmanager
def purge_context(db: Session) -> Iterator[None]:
    """Set ``app.purge_context='on'`` for the active transaction.

    The setting is automatically cleared at transaction end (LOCAL scope).
    We also explicitly reset it on exit as a defensive measure in case the
    caller keeps the session alive across transactions.
    """
    db.execute(text("SET LOCAL app.purge_context = 'on'"))
    try:
        yield
    finally:
        # ``RESET LOCAL`` is not valid; assigning empty string is the
        # conventional way to clear a custom GUC mid-transaction.
        try:
            db.execute(text("SET LOCAL app.purge_context = ''"))
        except Exception:  # noqa: BLE001 — defensive cleanup, never raise
            pass
