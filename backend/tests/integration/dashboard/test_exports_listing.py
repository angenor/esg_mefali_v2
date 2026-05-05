"""F52 US3 — Tests d'intégration ``GET /me/exports``.

Couvre : pagination keyset, filtre ``type``, masquage ``signed_url`` si expiré.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

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


def _insert_export(  # noqa: PLR0913
    *,
    account_id: str,
    user_id: str,
    type_: str = "rgpd_full",
    format_: str = "json",
    status_: str = "ready",
    size_bytes: int | None = 1024,
    signed_url: str | None = "https://eu-storage.example/exp/x",
    expires_in_days: int | None = 7,
    created_offset_seconds: int = 0,
    delivered_via: str | None = "inapp",
) -> uuid.UUID:
    eid = uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        seconds=created_offset_seconds
    )
    expires = (
        now + timedelta(days=expires_in_days) if expires_in_days is not None else None
    )
    sess = _engine_session()
    with sess() as s:
        s.execute(
            text(
                """
                INSERT INTO export_artifact
                  (id, account_id, user_id, type, format, size_bytes, status,
                   signed_url, signed_url_expires_at, created_at, ready_at,
                   delivered_via)
                VALUES
                  (CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:uid AS UUID),
                   CAST(:t AS export_type), :f, :sz,
                   CAST(:st AS export_status), :url, :exp, :ts,
                   CASE WHEN :st = 'ready' THEN :ts ELSE NULL END, :dv)
                """
            ),
            {
                "id": str(eid),
                "aid": account_id,
                "uid": user_id,
                "t": type_,
                "f": format_,
                "sz": size_bytes,
                "st": status_,
                "url": signed_url,
                "exp": expires,
                "ts": now,
                "dv": delivered_via,
            },
        )
        s.commit()
    return eid


def _cleanup(ids: list[uuid.UUID]) -> None:
    if not ids:
        return
    sess = _engine_session()
    with sess() as s:
        for eid in ids:
            s.execute(
                text("DELETE FROM export_artifact WHERE id = CAST(:id AS UUID)"),
                {"id": str(eid)},
            )
        s.commit()


@requires_db
class TestExportsListing:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get("/me/exports")
        assert r.status_code in {401, 403}

    def test_empty(self, client, unique_email, valid_password) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/exports")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["items"] == []
        assert body["next_cursor"] is None

    def test_lists_in_descending_creation_order(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        uid = me["id"]
        ids = [
            _insert_export(account_id=aid, user_id=uid, created_offset_seconds=-300),
            _insert_export(account_id=aid, user_id=uid, created_offset_seconds=-200),
            _insert_export(account_id=aid, user_id=uid, created_offset_seconds=-100),
        ]
        try:
            r = client.get("/me/exports")
            assert r.status_code == 200
            items = r.json()["items"]
            assert len(items) == 3
            # Most recent first
            order = [it["id"] for it in items]
            assert order == [str(ids[2]), str(ids[1]), str(ids[0])]
        finally:
            _cleanup(ids)

    def test_filter_by_type(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        uid = me["id"]
        ids = [
            _insert_export(account_id=aid, user_id=uid, type_="rgpd_full"),
            _insert_export(
                account_id=aid,
                user_id=uid,
                type_="report_pdf",
                format_="pdf",
            ),
        ]
        try:
            r = client.get("/me/exports?type=report_pdf")
            assert r.status_code == 200
            items = r.json()["items"]
            assert all(it["type"] == "report_pdf" for it in items)
            assert len(items) == 1
        finally:
            _cleanup(ids)

    def test_signed_url_hidden_when_expired(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        uid = me["id"]
        ids = [
            _insert_export(
                account_id=aid,
                user_id=uid,
                expires_in_days=-1,  # déjà expiré
            ),
        ]
        try:
            r = client.get("/me/exports")
            assert r.status_code == 200
            items = r.json()["items"]
            assert items[0]["signed_url"] is None
        finally:
            _cleanup(ids)

    def test_pagination_limit(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        uid = me["id"]
        ids = [
            _insert_export(
                account_id=aid, user_id=uid, created_offset_seconds=-i * 60
            )
            for i in range(5)
        ]
        try:
            r = client.get("/me/exports?limit=2")
            assert r.status_code == 200
            body = r.json()
            assert len(body["items"]) == 2
            assert body["next_cursor"] is not None
        finally:
            _cleanup(ids)
