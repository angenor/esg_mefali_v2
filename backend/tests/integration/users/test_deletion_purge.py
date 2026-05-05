"""F52 US2 — Test CLI ``purge_deletions``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _engine_session():
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    return sessionmaker(bind=get_engine_migrator(), future=True)


def _register_pme(client, email, password) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client.get("/me").json()


@requires_db
def test_purge_deletions_processes_due_requests(
    client, unique_email, valid_password
) -> None:
    me = _register_pme(client, unique_email, valid_password)
    aid = me["account_id"]
    uid = me["user_id"]

    # Insère manuellement une demande échue.
    sess = _engine_session()
    rid = uuid.uuid4()
    with sess() as s:
        now = datetime.now(UTC)
        past = now - timedelta(days=31)
        s.execute(
            text(
                """
                INSERT INTO account_deletion_request
                  (id, account_id, user_id, requested_at, scheduled_for,
                   status, confirmation_text)
                VALUES
                  (CAST(:rid AS UUID), CAST(:aid AS UUID), CAST(:uid AS UUID),
                   :past, :past, 'pending', 'X')
                """
            ),
            {
                "rid": str(rid),
                "aid": aid,
                "uid": uid,
                "past": past,
            },
        )
        s.commit()

    from app.users.cli import purge_deletions

    n = purge_deletions(dry_run=False)
    assert n >= 1

    with sess() as s:
        row = s.execute(
            text(
                "SELECT status, executed_at FROM account_deletion_request "
                "WHERE id = CAST(:rid AS UUID)"
            ),
            {"rid": str(rid)},
        ).first()
        assert row is not None
        assert row.status == "executed"
        assert row.executed_at is not None
