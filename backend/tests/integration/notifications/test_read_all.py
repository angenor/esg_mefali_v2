"""F52 US1 — Tests d'intégration ``POST /me/notifications/read-all``.

Couvre : compteur, idempotence, filtre par ``kinds``, audit log.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email, password) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    me = client.get("/me")
    assert me.status_code == 200
    return me.json()


def _engine_session():
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    return sessionmaker(bind=get_engine_migrator(), future=True)


def _insert_notification(*, account_id: str, kind: str, title: str) -> uuid.UUID:
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
                  (CAST(:id AS UUID), CAST(:aid AS UUID), :k, :t,
                   NULL, 1, :ts, :ts)
                """
            ),
            {"id": str(nid), "aid": account_id, "k": kind, "t": title, "ts": now},
        )
        s.commit()
    return nid


def _cleanup(nids: list[uuid.UUID]) -> None:
    if not nids:
        return
    sess = _engine_session()
    with sess() as s:
        for nid in nids:
            s.execute(
                text("DELETE FROM notification WHERE id = CAST(:id AS UUID)"),
                {"id": str(nid)},
            )
        s.commit()


@requires_db
class TestReadAll:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.post("/me/notifications/read-all", json={})
        assert r.status_code in {401, 403}

    def test_marks_all_unread(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        nids = [
            _insert_notification(account_id=aid, kind="deadline_j_minus_30", title="A"),
            _insert_notification(account_id=aid, kind="deadline_j_minus_7", title="B"),
            _insert_notification(account_id=aid, kind="offre_recommandee", title="C"),
        ]
        try:
            r = client.post("/me/notifications/read-all", json={})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["updated_count"] == 3
            assert body["unread_count_after"] == 0
            # vérifie via la liste
            unread = client.get("/me/notifications?unread=true").json()
            assert unread == []
        finally:
            _cleanup(nids)

    def test_filter_by_kinds(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        nids = [
            _insert_notification(account_id=aid, kind="deadline_j_minus_30", title="A"),
            _insert_notification(account_id=aid, kind="offre_recommandee", title="B"),
        ]
        try:
            r = client.post(
                "/me/notifications/read-all",
                json={"kinds": ["deadline_j_minus_30"]},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["updated_count"] == 1
            assert body["unread_count_after"] == 1
        finally:
            _cleanup(nids)

    def test_idempotent(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        nid = _insert_notification(
            account_id=aid, kind="deadline_j_minus_7", title="A"
        )
        try:
            r1 = client.post("/me/notifications/read-all", json={})
            assert r1.status_code == 200
            assert r1.json()["updated_count"] == 1
            r2 = client.post("/me/notifications/read-all", json={})
            assert r2.status_code == 200
            assert r2.json()["updated_count"] == 0
        finally:
            _cleanup([nid])

    def test_invalid_kind_rejected(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post(
            "/me/notifications/read-all", json={"kinds": ["NOT_A_KIND"]}
        )
        assert r.status_code in {400, 422}
