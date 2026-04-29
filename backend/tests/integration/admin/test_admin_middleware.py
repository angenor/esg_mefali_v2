"""F06 T022 — admin middleware: 200 admin, 403 PME, 401 anonymous."""

from __future__ import annotations

from tests.integration.conftest import requires_db


@requires_db
class TestAdminAccess:
    def test_anonymous_returns_401(self, client):
        client.cookies.clear()
        r = client.get("/admin/demo_indicator/")
        assert r.status_code == 401

    def test_pme_returns_403(self, pme_client):
        r = pme_client.get("/admin/demo_indicator/")
        assert r.status_code == 403

    def test_admin_returns_200(self, admin_client):
        r = admin_client.get("/admin/demo_indicator/")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total_estimate" in body

    def test_admin_unknown_entity_returns_404(self, admin_client):
        r = admin_client.get("/admin/no_such_entity/")
        assert r.status_code == 404
