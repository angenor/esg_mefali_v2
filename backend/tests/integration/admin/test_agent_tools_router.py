"""F58 / T035 — Tests intégration endpoints admin kill-switch (FR-007/8/9)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.agent.guardrails.tool_status import _reset_cache
from tests.conftest import requires_db


@pytest.fixture(autouse=True)
def _reset_tool_cache() -> None:
    _reset_cache()
    yield
    _reset_cache()


def _cleanup_status(db_engine: Engine, tool_name: str) -> None:
    with db_engine.connect() as conn:
        conn.execute(
            text("DELETE FROM agent_tool_status WHERE tool_name = :n"),
            {"n": tool_name},
        )
        conn.commit()


@requires_db
@pytest.mark.integration
def test_admin_can_disable_then_enable_tool(
    admin_client: TestClient, db_engine: Engine
) -> None:
    tool = "test_tool_disable_enable"
    _cleanup_status(db_engine, tool)

    # Disable
    r = admin_client.post(
        f"/admin/agent/tools/{tool}/disable",
        json={"reason": "test integration"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_name"] == tool
    assert body["enabled"] is False

    # Vérifier en DB via SessionLocal (pas db_engine — fixtures différentes).
    from app.db import SessionLocal as _SL

    with _SL() as sess:
        row = (
            sess.execute(
                text(
                    "SELECT enabled, reason FROM agent_tool_status WHERE tool_name = :n"
                ),
                {"n": tool},
            )
            .mappings()
            .first()
        )
        assert row is not None, f"row introuvable pour {tool}"
        assert row["enabled"] is False
        assert row["reason"] == "test integration"

    # Re-enable
    r = admin_client.post(f"/admin/agent/tools/{tool}/enable")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True

    _cleanup_status(db_engine, tool)


@requires_db
@pytest.mark.integration
def test_admin_get_tools_list(admin_client: TestClient) -> None:
    r = admin_client.get("/admin/agent/tools")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)


@requires_db
@pytest.mark.integration
def test_disable_invalid_tool_name_returns_404(admin_client: TestClient) -> None:
    bad_name = "weird/name with spaces"
    r = admin_client.post(
        f"/admin/agent/tools/{bad_name}/disable",
        json={"reason": "test"},
    )
    # FastAPI route matching peut renvoyer 404 directement, ou 422 si payload bad
    assert r.status_code in (404, 422)


@requires_db
@pytest.mark.integration
def test_disable_requires_reason_field(admin_client: TestClient) -> None:
    """Pydantic ``extra='forbid'`` + ``reason`` requis."""
    r = admin_client.post(
        "/admin/agent/tools/some_tool/disable",
        json={},  # missing reason
    )
    assert r.status_code == 422


@requires_db
@pytest.mark.integration
def test_disable_rejects_extra_fields(admin_client: TestClient) -> None:
    """Pydantic ``extra='forbid'``."""
    r = admin_client.post(
        "/admin/agent/tools/some_tool/disable",
        json={"reason": "x", "evil": "field"},
    )
    assert r.status_code == 422


@requires_db
@pytest.mark.integration
def test_non_admin_forbidden(client: TestClient, unique_email: str, valid_password: str) -> None:
    """Non-admin ne doit pas pouvoir accéder aux endpoints kill-switch."""
    client.cookies.clear()
    client.post(
        "/auth/register",
        json={"email": unique_email, "password": valid_password},
    )
    client.post(
        "/auth/login",
        json={"email": unique_email, "password": valid_password},
    )
    r = client.get("/admin/agent/tools")
    # 401/403/404 selon convention (P2 prefer 404 mais require_admin renvoie 403/401)
    assert r.status_code in (401, 403, 404)
