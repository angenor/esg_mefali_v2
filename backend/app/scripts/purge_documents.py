"""F50 US6 T071 — Job CLI ``purge_documents``.

Sélectionne les ``document_entreprise`` dont ``purge_scheduled_at <= now()``
et exécute :
1. Suppression du fichier sur le storage.
2. Suppression des liens ``document_link_projet`` (ON DELETE CASCADE).
3. Suppression de la ligne ``document_entreprise``.
4. Audit ``hard_purge`` source=``system``.

Usage : ``python -m app.scripts.purge_documents``
        ``python -m app.scripts.purge_documents --dry-run``

Conformément à la constitution P3 (audit append-only) et aux clarifications
RGPD/UEMOA (rétention 30 j).
"""

from __future__ import annotations

import argparse
import logging
import sys
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.config import get_settings
from app.core.session import set_db_session_context
from app.db import SessionLocal
from app.storage.local import LocalStorage

logger = logging.getLogger(__name__)


def _get_storage() -> LocalStorage:
    settings = get_settings()
    root = getattr(settings, "storage_root", None) or "backend/storage"
    return LocalStorage(root)


def purge_due_documents(db: Session, storage: LocalStorage, *, dry_run: bool = False) -> int:
    """Purge tous les documents dont la date de purge est échue. Retourne le nombre purgé.

    Chaque document est purgé dans sa propre transaction, avec ``SET LOCAL
    app.current_account_id`` correspondant — sinon les politiques RLS bloqueraient
    l'INSERT audit_log et le DELETE, ou (pire) traiteraient cross-tenant si le
    rôle DB porte ``BYPASSRLS``.
    """
    # Sélection : nécessite is_admin pour traverser tous les tenants.
    set_db_session_context(db, user_id=None, account_id=None, is_admin=True)
    rows = db.execute(
        text(
            "SELECT id, account_id, storage_path FROM document_entreprise "
            "WHERE deleted_at IS NOT NULL "
            "AND purge_scheduled_at IS NOT NULL "
            "AND purge_scheduled_at <= now()"
        )
    ).all()
    db.commit()

    purged = 0
    for r in rows:
        doc_id = r.id if isinstance(r.id, UUID) else UUID(str(r.id))
        account_id = r.account_id if isinstance(r.account_id, UUID) else UUID(str(r.account_id))
        if dry_run:
            logger.info("[dry-run] would purge document %s (account %s)", doc_id, account_id)
            purged += 1
            continue
        try:
            storage.delete(r.storage_path)
        except OSError as e:
            # H4: ne pas logger storage_path (chemin physique) — uniquement l'UUID.
            logger.warning("storage.delete failed for %s: %s", doc_id, e)
        # Pose le contexte RLS de l'account ciblé pour cette transaction.
        set_db_session_context(db, user_id=None, account_id=account_id, is_admin=False)
        # Audit AVANT suppression de la ligne (FK auditable).
        # H6: ne pas stocker storage_path (chemin physique) dans l'audit append-only.
        record_audit(
            db,
            entity_type="document_entreprise",
            entity_id=doc_id,
            field="hard_purge",
            old=None,
            new={"doc_id": str(doc_id)},
            source_of_change=SourceOfChange.SYSTEM,
            user_id=None,
            account_id=account_id,
            notes="document_entreprise.hard_purge",
        )
        # Suppression : les liens M:N sont en CASCADE.
        # Filtre explicite ``account_id`` en plus du RLS (defense-in-depth).
        db.execute(
            text(
                "DELETE FROM document_entreprise "
                "WHERE id = CAST(:id AS UUID) AND account_id = CAST(:aid AS UUID)"
            ),
            {"id": str(doc_id), "aid": str(account_id)},
        )
        db.commit()
        purged += 1
    return purged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Purge documents échus (RGPD 30 j).")
    parser.add_argument("--dry-run", action="store_true", help="N'effectue aucune suppression.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    db = SessionLocal()
    storage = _get_storage()
    try:
        n = purge_due_documents(db, storage, dry_run=args.dry_run)
        logger.info("Purgés : %d document(s)%s", n, " (dry-run)" if args.dry_run else "")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
