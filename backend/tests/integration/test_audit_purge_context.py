"""F05 — T007/T010: tests d'intégration trigger audit_log_immutable + purge_context.

Invariants vérifiés (Module 0):
- UPDATE/DELETE sur audit_log hors purge_context => exception.
- DELETE même sous purge_context => exception (le trigger réserve l'exception aux UPDATE).
- UPDATE colonne ``user_id`` SOUS purge_context => OK (RTBF).
- UPDATE colonne ``new_value`` SOUS purge_context => exception (seul user_id autorisé).
- ``scheduled_job_run`` table existe + UNIQUE(job_name, run_date).
"""

from __future__ import annotations

import json
import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import requires_db


@pytest.fixture()
def session(db_engine):
    Sess = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)
    s: Session = Sess()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def _ensure_account(session: Session) -> uuid.UUID:
    """Create a throwaway account row; returns its id."""
    aid = uuid.uuid4()
    session.execute(
        text("INSERT INTO account (id, name, created_at, updated_at) "
             "VALUES (:id, :n, now(), now())"),
        {"id": str(aid), "n": f"audit-test-{aid.hex[:8]}"},
    )
    session.commit()
    return aid


def _insert_audit_row(session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert one audit_log row directly via the migrator role; returns (id, account_id)."""
    rid = uuid.uuid4()
    eid = uuid.uuid4()
    aid = _ensure_account(session)
    session.execute(
        text(
            """
            INSERT INTO audit_log (id, user_id, account_id, entity_type, entity_id,
                field, old_value, new_value, source_of_change,
                "timestamp", created_at, updated_at, version)
            VALUES (:id, NULL, :aid, 'test_entity', :eid,
                'name', CAST(:old AS JSONB), CAST(:new AS JSONB),
                CAST('manual' AS source_of_change_t),
                now(), now(), now(), 1)
            """
        ),
        {
            "id": str(rid),
            "aid": str(aid),
            "eid": str(eid),
            "old": json.dumps("a"),
            "new": json.dumps("b"),
        },
    )
    session.commit()
    return rid, aid


@requires_db
def test_audit_update_outside_purge_context_raises(session):
    rid, _ = _insert_audit_row(session)
    with pytest.raises(DBAPIError) as exc:
        session.execute(
            text("UPDATE audit_log SET user_id = NULL WHERE id = :id"),
            {"id": str(rid)},
        )
        session.commit()
    assert "append-only" in str(exc.value).lower()
    session.rollback()


@requires_db
def test_audit_delete_always_raises(session):
    rid, _ = _insert_audit_row(session)
    # Even under purge_context, DELETE must be rejected.
    from app.services.audit_extension import purge_context

    with pytest.raises(DBAPIError) as exc:
        with purge_context(session):
            session.execute(text("DELETE FROM audit_log WHERE id = :id"), {"id": str(rid)})
            session.commit()
    assert "append-only" in str(exc.value).lower()
    session.rollback()


@requires_db
def test_audit_update_user_id_under_purge_context_ok(session):
    from app.services.audit_extension import purge_context

    rid, _ = _insert_audit_row(session)
    # Pseudonymisation simulée : user_id forcé à NULL. (Le helper
    # ``pseudonymize`` retourne un opaque string TEXT ; un futur sprint
    # ajoutera une colonne ``pseudonymous_user_id TEXT`` — voir DEFERRED.)
    with purge_context(session):
        session.execute(
            text("UPDATE audit_log SET user_id = NULL WHERE id = :id"),
            {"id": str(rid)},
        )
        got = session.execute(
            text("SELECT user_id FROM audit_log WHERE id = :id"), {"id": str(rid)}
        ).scalar()
        assert got is None
    session.commit()


@requires_db
def test_audit_update_other_column_under_purge_raises(session):
    from app.services.audit_extension import purge_context

    rid, _ = _insert_audit_row(session)
    with pytest.raises(DBAPIError) as exc:
        with purge_context(session):
            session.execute(
                text("UPDATE audit_log SET new_value = CAST(:v AS JSONB) WHERE id = :id"),
                {"v": json.dumps("tampered"), "id": str(rid)},
            )
    assert "only user_id" in str(exc.value).lower() or "purge context" in str(exc.value).lower()
    session.rollback()


@requires_db
def test_scheduled_job_run_unique_per_day(session):
    today = date.today()
    session.execute(
        text(
            "INSERT INTO scheduled_job_run (job_name, run_date, status) "
            "VALUES ('refresh_fx_rates', :d, 'success')"
        ),
        {"d": today},
    )
    session.commit()
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO scheduled_job_run (job_name, run_date, status) "
                "VALUES ('refresh_fx_rates', :d, 'success')"
            ),
            {"d": today},
        )
        session.commit()
    session.rollback()
    # cleanup
    session.execute(
        text("DELETE FROM scheduled_job_run WHERE job_name='refresh_fx_rates' AND run_date=:d"),
        {"d": today},
    )
    session.commit()
