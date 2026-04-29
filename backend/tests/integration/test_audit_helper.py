"""F04 — record_audit + enum closed-list integration tests (T030, T031, T051)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError, ProgrammingError

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from tests.conftest import DB_AVAILABLE

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_record_audit_inserts_one_row(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        eid = uuid4()
        rid = record_audit(
            db,
            entity_type="entreprise",
            entity_id=eid,
            field="nom",
            old="Old",
            new="New",
            source_of_change=SourceOfChange.MANUAL,
        )
        assert rid is not None
        row = db.execute(
            text(
                "SELECT entity_type, field, old_value, new_value, source_of_change, "
                '"timestamp" '
                "FROM audit_log WHERE id = :rid"
            ),
            {"rid": str(rid)},
        ).mappings().first()
        assert row is not None
        assert row["entity_type"] == "entreprise"
        assert row["field"] == "nom"
        assert row["old_value"] == "Old"
        assert row["new_value"] == "New"
        assert str(row["source_of_change"]) == "manual"
        assert row["timestamp"] is not None
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_record_audit_noop_when_old_eq_new(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        rid = record_audit(
            db,
            entity_type="projet",
            entity_id=uuid4(),
            field="nom",
            old="same",
            new="same",
        )
        assert rid is None
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_record_audit_create_event_has_null_field(db_engine) -> None:
    """T035 — POST-style create event: field=NULL, old_value=NULL."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        eid = uuid4()
        rid = record_audit(
            db,
            entity_type="projet",
            entity_id=eid,
            field=None,
            old=None,
            new={"nom": "Nouveau projet"},
            source_of_change=SourceOfChange.MANUAL,
        )
        row = db.execute(
            text(
                "SELECT field, old_value, new_value FROM audit_log WHERE id=:rid"
            ),
            {"rid": str(rid)},
        ).mappings().first()
        assert row["field"] is None
        assert row["old_value"] is None
        assert row["new_value"] == {"nom": "Nouveau projet"}
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_enum_closed_list_rejects_unknown_value(db_engine) -> None:
    """T051 — direct SQL insert with unknown source_of_change is rejected."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        with pytest.raises((DataError, IntegrityError, ProgrammingError, Exception)):
            db.execute(
                text(
                    "INSERT INTO audit_log "
                    "(id, entity_type, entity_id, source_of_change) "
                    "VALUES (gen_random_uuid(), 'x', gen_random_uuid(), "
                    "        CAST(:s AS source_of_change_t))"
                ),
                {"s": "unknown"},
            )
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_record_audit_redacts_blacklisted_field(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        rid = record_audit(
            db,
            entity_type="account_user",
            entity_id=uuid4(),
            field="password",
            old=None,
            new="hunter2",
        )
        row = db.execute(
            text("SELECT new_value FROM audit_log WHERE id=:rid"),
            {"rid": str(rid)},
        ).mappings().first()
        assert row["new_value"] == "[REDACTED]"
        db.rollback()
