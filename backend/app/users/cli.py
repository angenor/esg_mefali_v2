"""F52 US2 — CLI utilitaires utilisateurs.

Commande principale : ``python -m app.users.cli purge_deletions``.

Lit ``account_deletion_request WHERE status='pending' AND scheduled_for <= now()``,
anonymise/cascade RLS, met ``executed_at`` + audit ``system``.
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.db import get_engine_migrator
from app.models.account_deletion_request import AccountDeletionRequest

logger = logging.getLogger(__name__)


def _engine_session_factory():
    return sessionmaker(bind=get_engine_migrator(), future=True)


def _purge_account(db: Session, *, account_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Cascade safe-delete de l'account ; respecte RLS via la session migrator.

    En MVP on se contente de marquer ``account.deleted_at`` et
    ``account_user.deleted_at`` ; les rows métier restent en base mais ne sont
    plus accessibles via RLS (FK à ``account_id`` filtré). Une purge "hard"
    nécessitera un job dédié.
    """
    now = datetime.now(UTC)
    db.execute(
        text("UPDATE account SET deleted_at = :now WHERE id = CAST(:aid AS UUID)"),
        {"now": now, "aid": str(account_id)},
    )
    db.execute(
        text(
            "UPDATE account_user SET deleted_at = :now "
            "WHERE account_id = CAST(:aid AS UUID)"
        ),
        {"now": now, "aid": str(account_id)},
    )
    db.execute(
        text(
            "UPDATE refresh_tokens SET revoked_at = :now, revoked_reason = "
            "'account_deletion' WHERE user_id IN ("
            "  SELECT id FROM account_user WHERE account_id = CAST(:aid AS UUID)"
            ")"
        ),
        {"now": now, "aid": str(account_id)},
    )


def purge_deletions(*, dry_run: bool = False) -> int:
    """Exécute la purge des demandes échues. Retourne le nombre traité."""
    factory = _engine_session_factory()
    processed = 0
    with factory() as db:
        rows = (
            db.execute(
                select(AccountDeletionRequest)
                .where(AccountDeletionRequest.status == "pending")
                .where(AccountDeletionRequest.scheduled_for <= datetime.now(UTC))
            )
            .scalars()
            .all()
        )
        for r in rows:
            if dry_run:
                logger.info(
                    "[purge-deletions] dry-run id=%s account=%s scheduled_for=%s",
                    r.id,
                    r.account_id,
                    r.scheduled_for,
                )
                processed += 1
                continue
            try:
                _purge_account(db, account_id=r.account_id, user_id=r.user_id)
                r.status = "executed"
                r.executed_at = datetime.now(UTC)
                record_audit(
                    db,
                    entity_type="account_deletion_request",
                    entity_id=r.id,
                    field="status",
                    old="pending",
                    new="executed",
                    source_of_change=SourceOfChange.SYSTEM,
                    user_id=r.user_id,
                    account_id=r.account_id,
                )
                processed += 1
            except Exception as exc:  # noqa: BLE001 — continue purge en cas d'erreur unitaire
                logger.exception("[purge-deletions] failed id=%s: %s", r.id, exc)
                continue
        if not dry_run:
            db.commit()
    return processed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.users.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pd = sub.add_parser("purge_deletions", help="Exécute la purge des comptes échus.")
    pd.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    if args.cmd == "purge_deletions":
        n = purge_deletions(dry_run=args.dry_run)
        print(f"purge_deletions: {n} request(s) processed (dry_run={args.dry_run})")
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main(sys.argv[1:]))
