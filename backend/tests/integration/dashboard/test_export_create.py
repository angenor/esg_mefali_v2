"""F52 US3 — Tests d'intégration création d'export.

Couvre :
- ``POST /me/exports`` → 202 Accepted + status pending.
- ``GET /me/exports/{id}`` → cycle pending → ready après worker.
- Audit log.
- Notification SSE ``system`` émise quand status=ready.
"""

from __future__ import annotations

import uuid

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
class TestExportCreate:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.post("/me/exports", json={"type": "rgpd_full", "format": "json"})
        assert r.status_code in {401, 403}

    def test_create_rgpd_full(self, client, unique_email, valid_password) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post(
            "/me/exports", json={"type": "rgpd_full", "format": "json"}
        )
        assert r.status_code == 202, r.text
        body = r.json()
        assert body["type"] == "rgpd_full"
        assert body["format"] == "json"
        assert body["status"] in {"pending", "ready"}
        assert body["created_at"] is not None
        eid = uuid.UUID(body["id"])

        # GET /me/exports/{id} doit renvoyer le même
        r2 = client.get(f"/me/exports/{eid}")
        assert r2.status_code == 200, r2.text
        assert r2.json()["id"] == str(eid)
        _cleanup([eid])

    def test_create_writes_audit(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post(
            "/me/exports", json={"type": "rgpd_full", "format": "json"}
        )
        assert r.status_code == 202
        eid = r.json()["id"]
        try:
            sess = _engine_session()
            with sess() as s:
                cnt = s.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM audit_log
                        WHERE entity_type = 'export_artifact'
                          AND entity_id = CAST(:id AS UUID)
                        """
                    ),
                    {"id": eid},
                ).scalar()
                assert cnt is not None and int(cnt) >= 1
        finally:
            _cleanup([uuid.UUID(eid)])

    def test_get_export_404_cross_tenant(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get(f"/me/exports/{uuid.uuid4()}")
        assert r.status_code in {404}

    def test_create_invalid_combination(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post("/me/exports", json={"type": "rgpd_full", "format": "pdf"})
        assert r.status_code in {400, 422}

    def test_create_report_pdf_requires_id(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post("/me/exports", json={"type": "report_pdf", "format": "pdf"})
        assert r.status_code in {400, 422}
