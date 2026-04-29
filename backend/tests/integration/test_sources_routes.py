"""F03 US1 — Tests integration routes Source."""

from __future__ import annotations

import time
import uuid

import pytest

from app.db import SessionLocal, get_engine_migrator
from app.scripts.seed_admin import create_admin
from app.services import source_service
from tests.integration.conftest import requires_db


def _stub_emb(_):
    return [[0.0] * 1024]


@pytest.fixture()
def seeded_source():
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"src_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        b = create_admin(
            db,
            email=f"src_b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        db.commit()
        a_id = a.id
        b_id = b.id
    finally:
        db.close()
    eng = get_engine_migrator()
    with eng.begin() as c:
        sid = source_service.create_pending(
            c,
            captured_by=a_id,
            url="https://x.example/route",
            title="Route Test",
            publisher="GCF",
        )
        source_service.verify(c, source_id=sid, verifier_id=b_id, embedding_func=_stub_emb)
    return sid


@requires_db
class TestSourcesRoutes:
    def test_get_source_by_id_public(self, client, seeded_source):
        r = client.get(f"/sources/{seeded_source}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == str(seeded_source)
        assert body["verification_status"] == "verified"

    def test_get_source_not_found(self, client):
        r = client.get(f"/sources/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_list_sources_requires_auth(self, client):
        client.cookies.clear()
        r = client.get("/sources")
        assert r.status_code in (401, 403)

    def test_list_sources_pme_forbidden(self, client, unique_email, valid_password):
        r = client.post(
            "/auth/register", json={"email": unique_email, "password": valid_password}
        )
        assert r.status_code == 201
        r = client.get("/sources")
        assert r.status_code == 403

    def test_list_sources_admin_ok(self, client, valid_password):
        # crée un admin via seed
        db = SessionLocal()
        email = f"adm_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
        try:
            create_admin(db, email=email, password=valid_password)
            db.commit()
        finally:
            db.close()
        client.cookies.clear()
        r = client.post("/auth/login", json={"email": email, "password": valid_password})
        assert r.status_code == 200, r.text
        # Set CSRF header for subsequent calls
        csrf = client.cookies.get("mefali_csrf")
        client.headers["x-csrf-token"] = csrf or ""

        r = client.get("/sources?limit=5")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body and "total" in body
