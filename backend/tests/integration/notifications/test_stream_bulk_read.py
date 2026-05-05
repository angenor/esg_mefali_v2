"""F52 US1 — Test SSE ``notification.bulk_read`` émis après mark-all-read.

La stream actuelle (F38) est un keepalive ; F52 ajoute un broker mémoire pour
publier les événements métier vers les flux ouverts. Ce test vérifie le
contrat : après ``POST /me/notifications/read-all``, un event est publié dans
le broker pour le compte concerné.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email, password) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    me = client.get("/me")
    return me.json()


def _engine_session():
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    return sessionmaker(bind=get_engine_migrator(), future=True)


def _insert_unread(*, account_id: str, kind: str = "offre_recommandee") -> uuid.UUID:
    nid = uuid.uuid4()
    sess = _engine_session()
    with sess() as s:
        now = datetime.now(UTC).replace(tzinfo=None)
        s.execute(
            text(
                """
                INSERT INTO notification
                  (id, account_id, kind, title, read_at,
                   version, created_at, updated_at)
                VALUES
                  (CAST(:id AS UUID), CAST(:aid AS UUID), :k, 't', NULL,
                   1, :ts, :ts)
                """
            ),
            {"id": str(nid), "aid": account_id, "k": kind, "ts": now},
        )
        s.commit()
    return nid


def _cleanup(nids: list[uuid.UUID]) -> None:
    sess = _engine_session()
    with sess() as s:
        for nid in nids:
            s.execute(
                text("DELETE FROM notification WHERE id = CAST(:id AS UUID)"),
                {"id": str(nid)},
            )
        s.commit()


@requires_db
@pytest.mark.asyncio
async def test_bulk_read_event_published(
    client, unique_email, valid_password
) -> None:
    """``mark_all_read`` doit publier un event ``notification.bulk_read``."""
    from app.notifications.broker import notifications_broker

    me = _register_pme(client, unique_email, valid_password)
    aid = me["account_id"]
    nid = _insert_unread(account_id=aid)

    try:
        # Souscrit au broker AVANT l'émission
        queue = notifications_broker.subscribe(account_id=uuid.UUID(aid))
        try:
            r = client.post("/me/notifications/read-all", json={})
            assert r.status_code == 200, r.text

            # Vérifie qu'au moins un event bulk_read est arrivé dans la queue
            event = await queue.get()
            assert event["event"] == "notification.bulk_read"
            payload = event["data"]
            assert payload["count"] == 1
        finally:
            notifications_broker.unsubscribe(uuid.UUID(aid), queue)
    finally:
        _cleanup([nid])
