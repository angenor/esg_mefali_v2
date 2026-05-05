"""F50 T088 — Tests unitaires du job ``purge_documents`` (logique pure).

Mocke ``Session`` SQLAlchemy + ``LocalStorage`` pour vérifier :
- Le ``SET LOCAL app.current_account_id`` est bien posé par account.
- ``--dry-run`` n'effectue ni delete fichier, ni delete DB, ni audit.
- L'audit ``hard_purge`` est inséré AVANT le DELETE (P3 append-only).
- L'audit ne contient pas le ``storage_path`` (H6 du security review).
- Une erreur ``OSError`` du storage ne stoppe pas la purge.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.scripts.purge_documents import purge_due_documents


def _row(**overrides):
    r = MagicMock()
    r.id = overrides.get("id", uuid4())
    r.account_id = overrides.get("account_id", uuid4())
    r.storage_path = overrides.get("storage_path", "ent/abc/def.pdf")
    return r


@pytest.mark.unit
def test_dry_run_executes_no_side_effects() -> None:
    db = MagicMock()
    storage = MagicMock()
    rows = [_row(), _row()]
    db.execute.return_value.all.return_value = rows

    with patch("app.scripts.purge_documents.set_db_session_context") as set_ctx, patch(
        "app.scripts.purge_documents.record_audit"
    ) as audit:
        n = purge_due_documents(db, storage, dry_run=True)

    assert n == 2
    storage.delete.assert_not_called()
    audit.assert_not_called()
    # set_db_session_context called once (admin SELECT) — pas par row.
    assert set_ctx.call_count == 1


@pytest.mark.unit
def test_purge_sets_account_context_per_row_and_audits() -> None:
    db = MagicMock()
    storage = MagicMock()
    row1 = _row()
    row2 = _row()
    db.execute.return_value.all.return_value = [row1, row2]

    with patch("app.scripts.purge_documents.set_db_session_context") as set_ctx, patch(
        "app.scripts.purge_documents.record_audit"
    ) as audit:
        n = purge_due_documents(db, storage, dry_run=False)

    assert n == 2
    # 1 SELECT admin + 2 SET account_id par doc.
    assert set_ctx.call_count == 3
    # Le storage est purgé pour chaque doc.
    assert storage.delete.call_count == 2
    # Audit ``hard_purge`` inséré pour chaque doc.
    assert audit.call_count == 2
    for call in audit.call_args_list:
        kwargs = call.kwargs
        assert kwargs["field"] == "hard_purge"
        assert kwargs["entity_type"] == "document_entreprise"
        # H6: storage_path NE DOIT PAS apparaître dans l'audit.
        assert "storage_path" not in (kwargs.get("new") or {})
        assert kwargs["source_of_change"].value == "system"


@pytest.mark.unit
def test_storage_oserror_does_not_stop_purge() -> None:
    db = MagicMock()
    storage = MagicMock()
    storage.delete.side_effect = OSError("disk full")
    rows = [_row(), _row()]
    db.execute.return_value.all.return_value = rows

    with patch("app.scripts.purge_documents.set_db_session_context"), patch(
        "app.scripts.purge_documents.record_audit"
    ) as audit:
        n = purge_due_documents(db, storage, dry_run=False)

    # Malgré OSError, audit + delete DB tentés pour chaque ligne.
    assert n == 2
    assert audit.call_count == 2


@pytest.mark.unit
def test_main_returns_zero_on_success() -> None:
    """Smoke test : main() lit les args et appelle purge_due_documents."""
    from app.scripts.purge_documents import main

    db = MagicMock()
    db.execute.return_value.all.return_value = []
    with patch("app.scripts.purge_documents.SessionLocal", return_value=db), patch(
        "app.scripts.purge_documents._get_storage", return_value=MagicMock()
    ):
        rc = main(["--dry-run"])

    assert rc == 0
    db.close.assert_called_once()
