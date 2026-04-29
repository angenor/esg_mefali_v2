"""F23 — Tests fonctionnels minimum du routeur (auth gate, 401)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.scoring.router import _validate_entity_type


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


class TestEntityTypeValidator:
    def test_valid_entreprise(self) -> None:
        _validate_entity_type("entreprise")  # ne lève pas

    def test_valid_projet(self) -> None:
        _validate_entity_type("projet")

    def test_invalid_raises_404(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            _validate_entity_type("offre")
        assert exc.value.status_code == 404


class TestAuthGate:
    """Sans JWT, toutes les routes de scoring doivent être bloquées."""

    def test_list_requires_auth(self, client: TestClient) -> None:
        eid = uuid.uuid4()
        resp = client.get(f"/me/scoring/entreprise/{eid}")
        assert resp.status_code in {401, 403}

    def test_detail_requires_auth(self, client: TestClient) -> None:
        eid = uuid.uuid4()
        resp = client.get(f"/me/scoring/entreprise/{eid}/ESG_MEFALI")
        assert resp.status_code in {401, 403}

    def test_recompute_requires_auth(self, client: TestClient) -> None:
        eid = uuid.uuid4()
        resp = client.post(
            f"/me/scoring/entreprise/{eid}/recompute?referentiel=ESG_MEFALI"
        )
        assert resp.status_code in {401, 403}


class TestRouterRegistered:
    def test_routes_present_in_openapi(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert any(p.startswith("/me/scoring/") for p in paths.keys())
