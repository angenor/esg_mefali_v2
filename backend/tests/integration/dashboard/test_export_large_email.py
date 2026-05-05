"""F52 US3 — Bascule e-mail lorsque ``size_bytes > 100 MB``.

L'export RGPD synthétique est forcé à dépasser 100 MB via un fixture/monkey-patch
sur la fonction de génération ; on vérifie que ``delivered_via='email'`` et que
``signed_url`` n'est PAS retourné dans la réponse au client.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text

from tests.integration.conftest import requires_db

LARGE = 200 * 1024 * 1024  # 200 MB


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
class TestExportLargeEmail:
    def test_large_export_switches_to_email(
        self, client, unique_email, valid_password, monkeypatch
    ) -> None:
        _register_pme(client, unique_email, valid_password)

        # On force le worker synchrone à produire un export de 200 MB
        from app.dashboard import exports_service

        original = exports_service._build_payload  # type: ignore[attr-defined]

        def _fake_payload(*args, **kwargs):
            payload, _ = original(*args, **kwargs)
            return payload, LARGE

        monkeypatch.setattr(exports_service, "_build_payload", _fake_payload)

        r = client.post(
            "/me/exports", json={"type": "rgpd_full", "format": "json"}
        )
        assert r.status_code == 202, r.text
        eid = r.json()["id"]
        try:
            r2 = client.get(f"/me/exports/{eid}")
            assert r2.status_code == 200, r2.text
            body = r2.json()
            assert body["status"] == "ready"
            assert body["delivered_via"] == "email"
            assert body.get("signed_url") is None
            assert body["size_bytes"] == LARGE
        finally:
            _cleanup([uuid.UUID(eid)])
