"""F04 — Audit log query service (T100, FR-017, SC-006)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.audit.service import MAX_PAGE_SIZE, list_entries
from tests.conftest import DB_AVAILABLE

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_list_entries_pagination_and_filters(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        # Seed a unique tag so we can isolate this test's rows.
        tag = f"f04test-{uuid4()}"
        eid = uuid4()
        for i in range(3):
            record_audit(
                db,
                entity_type=tag,
                entity_id=eid,
                field="x",
                old=i,
                new=i + 1,
                source_of_change=SourceOfChange.MANUAL,
            )

        page = list_entries(db, entity_type=tag, page=1, page_size=2)
        assert page.total == 3
        assert len(page.items) == 2
        assert page.page_size == 2

        page2 = list_entries(db, entity_type=tag, page=2, page_size=2)
        assert len(page2.items) == 1

        # Clamp test (FR-017, SC-006).
        clamped = list_entries(db, entity_type=tag, page=1, page_size=99999)
        assert clamped.page_size == MAX_PAGE_SIZE
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_list_entries_filter_by_source(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        tag = f"f04src-{uuid4()}"
        eid = uuid4()
        record_audit(db, entity_type=tag, entity_id=eid, field="a", old=1, new=2,
                     source_of_change=SourceOfChange.MANUAL)
        record_audit(db, entity_type=tag, entity_id=eid, field="b", old=1, new=2,
                     source_of_change=SourceOfChange.LLM)
        page = list_entries(
            db, entity_type=tag, source_of_change=SourceOfChange.LLM,
        )
        assert page.total == 1
        assert page.items[0].source_of_change == SourceOfChange.LLM
        # SQL-level audit: exact column value
        row = db.execute(
            text(
                "SELECT source_of_change::text AS s FROM audit_log "
                "WHERE entity_type = :t AND field='b'"
            ),
            {"t": tag},
        ).mappings().first()
        assert row["s"] == "llm"
        db.rollback()
