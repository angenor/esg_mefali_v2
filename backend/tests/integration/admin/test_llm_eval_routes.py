"""F35 — Tests d'intégration pour ``POST /api/admin/llm-eval/run``."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from tests.conftest import DB_AVAILABLE


def _schema_ready() -> bool:
    """Vrai si la table ``account_user`` existe (schema migré)."""
    if not DB_AVAILABLE:
        return False
    try:
        from app.config import get_settings

        engine = create_engine(get_settings().database_url, pool_pre_ping=False)
        with engine.connect() as conn:
            r = conn.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_name='account_user')"
                )
            )
            ok = bool(r.scalar())
        engine.dispose()
        return ok
    except Exception:
        return False


SCHEMA_READY = _schema_ready()

requires_db = pytest.mark.skipif(
    not SCHEMA_READY,
    reason="Postgres indisponible ou non migré — alembic upgrade head.",
)


@requires_db
@pytest.mark.integration
def test_run_requires_auth(client: TestClient) -> None:
    """Anonyme : 401 (pas de session) ou 403 (CSRF rejeté en amont)."""
    r = client.post("/api/admin/llm-eval/run", json={})
    assert r.status_code in (401, 403)


@requires_db
@pytest.mark.integration
def test_run_forbidden_for_pme(pme_client: TestClient) -> None:
    r = pme_client.post("/api/admin/llm-eval/run", json={})
    assert r.status_code == 403


@requires_db
@pytest.mark.integration
def test_run_returns_report_for_admin(admin_client: TestClient) -> None:
    r = admin_client.post("/api/admin/llm-eval/run", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "total" in body
    assert body["total"] >= 10
    assert body["passed"] + body["failed"] == body["total"]
    assert "metrics" in body
    assert {"tool_match_rate", "payload_partial_match_rate", "fallback_rate"} <= set(
        body["metrics"]
    )
    assert isinstance(body["cases"], list)
    assert body["cases"][0]["id"]
    failed_non_fallback = [
        c
        for c in body["cases"]
        if c["status"] == "failed" and c["expected_tool"] != "__fallback__"
    ]
    assert failed_non_fallback == [], failed_non_fallback


@requires_db
@pytest.mark.integration
def test_run_filter_by_tags(admin_client: TestClient) -> None:
    r = admin_client.post(
        "/api/admin/llm-eval/run", json={"tags": ["forme_juridique"]}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    ids = [c["id"] for c in body["cases"]]
    assert "qcu-forme-juridique" in ids


@requires_db
@pytest.mark.integration
def test_run_with_limit(admin_client: TestClient) -> None:
    r = admin_client.post("/api/admin/llm-eval/run", json={"limit": 2})
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 2


@requires_db
@pytest.mark.integration
def test_run_rejects_extra_fields(admin_client: TestClient) -> None:
    r = admin_client.post("/api/admin/llm-eval/run", json={"unknown": True})
    assert r.status_code == 422


@requires_db
@pytest.mark.integration
def test_run_with_no_body(admin_client: TestClient) -> None:
    r = admin_client.post("/api/admin/llm-eval/run")
    assert r.status_code == 200, r.text
