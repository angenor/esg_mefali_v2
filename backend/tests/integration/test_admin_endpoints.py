"""T046 — Tests integration /admin/_rls_check (admin/PME/anon)."""

from __future__ import annotations

import time
import uuid

from app.db import SessionLocal
from app.scripts.seed_admin import create_admin
from tests.integration.conftest import requires_db


@requires_db
class TestAdminRlsCheck:
    def test_anonymous_returns_401(self, client):
        client.cookies.clear()
        r = client.get("/admin/_rls_check")
        assert r.status_code == 401

    def test_pme_returns_403(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        r = client.get("/admin/_rls_check")
        assert r.status_code == 403

    def test_admin_returns_200(self, client, valid_password):
        # Crée admin via le helper
        email = f"admin_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
        db = SessionLocal()
        try:
            create_admin(db, email=email, password=valid_password)
            db.commit()
        finally:
            db.close()
        client.cookies.clear()
        r = client.post(
            "/auth/login", json={"email": email, "password": valid_password}
        )
        assert r.status_code == 200
        r2 = client.get("/admin/_rls_check")
        assert r2.status_code == 200
        body = r2.json()
        assert "tables_checked" in body
        assert "all_rls_enforced" in body
