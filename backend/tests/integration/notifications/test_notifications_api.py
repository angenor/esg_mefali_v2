"""F34 — Tests d'intégration des routes /me/notifications."""

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


def _insert_notification(
    *,
    account_id: str,
    kind: str = "offre_recommandee",
    title: str = "Test",
    body: str | None = None,
    read_at: datetime | None = None,
) -> uuid.UUID:
    nid = uuid.uuid4()
    sess = _engine_session()
    with sess() as s:
        now = datetime.now(UTC).replace(tzinfo=None)
        s.execute(
            text(
                """
                INSERT INTO notification
                  (id, account_id, kind, title, body, read_at,
                   version, created_at, updated_at)
                VALUES
                  (CAST(:id AS UUID), CAST(:aid AS UUID), :k, :t, :b,
                   :ra, 1, :ts, :ts)
                """
            ),
            {
                "id": str(nid),
                "aid": account_id,
                "k": kind,
                "t": title,
                "b": body,
                "ra": read_at,
                "ts": now,
            },
        )
        s.commit()
    return nid


def _cleanup_notification(nid: uuid.UUID) -> None:
    sess = _engine_session()
    with sess() as s:
        s.execute(
            text("DELETE FROM notification WHERE id = CAST(:id AS UUID)"),
            {"id": str(nid)},
        )
        s.commit()


@requires_db
class TestListNotifications:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get("/me/notifications")
        assert r.status_code in {401, 403}

    def test_returns_empty_for_new_pme(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/notifications")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_notifications_desc(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        ids = [
            _insert_notification(account_id=aid, kind="deadline_j_minus_30", title="A"),
            _insert_notification(account_id=aid, kind="deadline_j_minus_7", title="B"),
        ]
        try:
            r = client.get("/me/notifications")
            assert r.status_code == 200
            body = r.json()
            assert len(body) == 2
            # B inséré après A => DESC
            assert body[0]["title"] == "B"
            assert body[1]["title"] == "A"
        finally:
            for nid in ids:
                _cleanup_notification(nid)

    def test_unread_filter(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        n_unread = _insert_notification(account_id=aid, title="unread")
        n_read = _insert_notification(
            account_id=aid,
            title="read",
            read_at=datetime.now(UTC).replace(tzinfo=None),
        )
        try:
            r = client.get("/me/notifications?unread=true")
            assert r.status_code == 200
            titles = [it["title"] for it in r.json()]
            assert "unread" in titles
            assert "read" not in titles
        finally:
            _cleanup_notification(n_unread)
            _cleanup_notification(n_read)

    def test_pagination_limit_offset(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        ids = [
            _insert_notification(account_id=aid, title=f"N{i}") for i in range(3)
        ]
        try:
            r = client.get("/me/notifications?limit=1&offset=1")
            assert r.status_code == 200
            assert len(r.json()) == 1
        finally:
            for nid in ids:
                _cleanup_notification(nid)


@requires_db
class TestMarkRead:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.patch(f"/me/notifications/{uuid.uuid4()}/read")
        assert r.status_code in {401, 403}

    def test_marks_unread_as_read(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        nid = _insert_notification(account_id=aid, title="X")
        try:
            r = client.patch(f"/me/notifications/{nid}/read")
            assert r.status_code == 200, r.text
            assert r.json()["id"] == str(nid)
            assert r.json()["read_at"] is not None
            r2 = client.get("/me/notifications?unread=true")
            assert all(it["id"] != str(nid) for it in r2.json())
        finally:
            _cleanup_notification(nid)

    def test_404_when_not_owned(
        self, client, unique_email, valid_password
    ) -> None:
        me1 = _register_pme(client, unique_email, valid_password)
        aid1 = me1["account_id"]
        nid = _insert_notification(account_id=aid1, title="ownerA")
        try:
            client.cookies.clear()
            client.headers.pop("X-CSRF-Token", None)
            email2 = f"itest_other_{uuid.uuid4().hex[:8]}@example.com"
            _register_pme(client, email2, valid_password)
            r = client.patch(f"/me/notifications/{nid}/read")
            assert r.status_code == 404
        finally:
            _cleanup_notification(nid)

    def test_idempotent(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        nid = _insert_notification(account_id=aid, title="Y")
        try:
            r1 = client.patch(f"/me/notifications/{nid}/read")
            assert r1.status_code == 200
            first_read_at = r1.json()["read_at"]
            r2 = client.patch(f"/me/notifications/{nid}/read")
            assert r2.status_code == 200
            assert r2.json()["read_at"] == first_read_at
        finally:
            _cleanup_notification(nid)
