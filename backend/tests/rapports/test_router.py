"""F24 — Tests fonctionnels minimum du routeur (auth gate, openapi)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


class TestAuthGate:
    """Sans JWT, toutes les routes /me/rapports doivent être bloquées."""

    def test_create_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/me/rapports/conformite",
            json={
                "entity_id": str(uuid.uuid4()),
                "referentiels": ["ESG_MEFALI"],
            },
        )
        assert resp.status_code in {401, 403}

    def test_list_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/me/rapports")
        assert resp.status_code in {401, 403}

    def test_download_requires_auth(self, client: TestClient) -> None:
        rid = uuid.uuid4()
        resp = client.get(f"/me/rapports/{rid}/download")
        assert resp.status_code in {401, 403}


class TestRouterRegistered:
    def test_routes_present_in_openapi(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert any(p.startswith("/me/rapports") for p in paths.keys())
        assert "/me/rapports/conformite" in paths
