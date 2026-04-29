"""F07 — US1 : tests HTTP du router ``/admin/sources``."""

from __future__ import annotations

import uuid

from tests.integration.conftest import requires_db


@requires_db
class TestAdminSourcesRouter:
    def test_post_create_returns_201(self, admin_client):
        unique = f"path/{uuid.uuid4()}"
        r = admin_client.post(
            "/admin/sources",
            json={
                "url": f"http://www.example.com/{unique}/?utm_source=x",
                "title": "My Source",
                "publisher": "ACME",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["source"]["verification_status"] == "pending"
        assert body["source"]["canonical_url"] == f"https://example.com/{unique}"
        assert body["head_warning"] is None

    def test_post_invalid_url_returns_422(self, admin_client):
        r = admin_client.post(
            "/admin/sources",
            json={"url": "not-a-url", "title": "x", "publisher": "y"},
        )
        assert r.status_code == 422

    def test_post_duplicate_returns_409(self, admin_client):
        unique = f"dup/{uuid.uuid4()}"
        url = f"https://example.com/{unique}"
        r1 = admin_client.post(
            "/admin/sources",
            json={"url": url, "title": "t1", "publisher": "P", "page": "1"},
        )
        assert r1.status_code == 201, r1.text
        sid1 = r1.json()["source"]["id"]

        r2 = admin_client.post(
            "/admin/sources",
            json={
                "url": f"http://www.example.com/{unique}/?utm_source=x",
                "title": "t2",
                "publisher": "P",
                "page": "1",
            },
        )
        assert r2.status_code == 409, r2.text
        detail = r2.json()["detail"]
        assert detail["code"] == "duplicate_source"
        assert detail["existing_id"] == sid1

    def test_post_requires_admin(self, client):
        r = client.post(
            "/admin/sources",
            json={"url": "https://example.com/x", "title": "t", "publisher": "p"},
        )
        # 401 (no auth) ou 403 (auth non-admin) — refus dans les deux cas
        assert r.status_code in (401, 403)

    def test_get_existing_returns_200(self, admin_client):
        unique = f"get/{uuid.uuid4()}"
        r = admin_client.post(
            "/admin/sources",
            json={
                "url": f"https://example.com/{unique}",
                "title": "t",
                "publisher": "p",
            },
        )
        sid = r.json()["source"]["id"]
        r2 = admin_client.get(f"/admin/sources/{sid}")
        assert r2.status_code == 200
        assert r2.json()["id"] == sid

    def test_get_unknown_returns_404(self, admin_client):
        r = admin_client.get(f"/admin/sources/{uuid.uuid4()}")
        assert r.status_code == 404
