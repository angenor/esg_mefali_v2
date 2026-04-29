"""F10 US1 T021 — Integration tests for ``GET /admin/pme``."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.integration.conftest import requires_db


@requires_db
def test_list_pme_requires_admin(client: TestClient) -> None:
    """Anonymous → 401."""
    r = client.get("/admin/pme")
    assert r.status_code in (401, 403), r.text


@requires_db
def test_list_pme_pme_user_forbidden(pme_client: TestClient) -> None:
    """A PME user cannot reach /admin/pme."""
    r = pme_client.get("/admin/pme")
    assert r.status_code == 403, r.text


@requires_db
def test_list_pme_admin_ok(admin_client: TestClient) -> None:
    r = admin_client.get("/admin/pme?limit=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body and "total" in body
    assert isinstance(body["items"], list)
    assert body["limit"] == 5


@requires_db
def test_list_pme_search_filter(admin_client: TestClient) -> None:
    """Search by free text — returns 200 even when nothing matches."""
    r = admin_client.get("/admin/pme?q=zzznotfoundzzz")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []
