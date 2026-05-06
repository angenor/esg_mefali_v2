"""F56 / T047 — Tests integration de ``GET /admin/agent/metrics/sourcing``."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.admin.agent_metrics import reset_metrics_cache
from tests.conftest import requires_db


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metrics_cache()
    yield
    reset_metrics_cache()


@requires_db
@pytest.mark.integration
def test_admin_can_access_metrics(admin_client: TestClient):
    r = admin_client.get("/admin/agent/metrics/sourcing?period=7d")
    assert r.status_code == 200, r.text
    body = r.json()
    # Pydantic shape check
    assert body["period"] == "7d"
    assert "compliance_rate" in body
    assert 0.0 <= body["compliance_rate"] <= 1.0
    assert 0.0 <= body["unsourced_rate"] <= 1.0
    assert 0.0 <= body["retry_rate"] <= 1.0
    assert 0.0 <= body["fallback_rate"] <= 1.0
    assert body["total_runs"] >= 0
    assert isinstance(body["top_sources"], list)
    assert isinstance(body["top_unsourced_topics"], list)


@requires_db
@pytest.mark.integration
def test_pme_user_forbidden(client: TestClient, unique_email: str, valid_password: str):
    # Register a PME (non-admin) user
    client.cookies.clear()
    client.post(
        "/auth/register",
        json={"email": unique_email, "password": valid_password},
    )
    r = client.get("/admin/agent/metrics/sourcing")
    assert r.status_code in (401, 403), r.text


@requires_db
@pytest.mark.integration
def test_period_validation(admin_client: TestClient):
    r = admin_client.get("/admin/agent/metrics/sourcing?period=invalid")
    assert r.status_code == 422


@requires_db
@pytest.mark.integration
def test_default_period_is_7d(admin_client: TestClient):
    r = admin_client.get("/admin/agent/metrics/sourcing")
    assert r.status_code == 200
    assert r.json()["period"] == "7d"


@requires_db
@pytest.mark.integration
def test_cache_reuses_response_within_ttl(admin_client: TestClient):
    r1 = admin_client.get("/admin/agent/metrics/sourcing?period=30d")
    assert r1.status_code == 200
    body1 = r1.json()
    r2 = admin_client.get("/admin/agent/metrics/sourcing?period=30d")
    assert r2.status_code == 200
    body2 = r2.json()
    # computed_at devrait être identique (cache hit)
    assert body1["computed_at"] == body2["computed_at"]
