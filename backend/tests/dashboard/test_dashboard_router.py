"""F32 — Tests fonctionnels du routeur dashboard (auth gate + registration)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


class TestAuthGate:
    """Sans session PME, toutes les routes dashboard doivent être bloquées."""

    def test_summary_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/me/dashboard/summary")
        assert resp.status_code in {401, 403}

    def test_export_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/me/data/export")
        assert resp.status_code in {401, 403}


class TestRouterRegistered:
    def test_summary_path_in_openapi(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert "/me/dashboard/summary" in paths

    def test_export_path_in_openapi(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert "/me/data/export" in paths

    def test_response_schemas_in_openapi(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        schemas = resp.json().get("components", {}).get("schemas", {})
        assert "DashboardSummaryOut" in schemas
        assert "DataExportOut" in schemas
