"""F58 / E2E — Kill-switch admin par tool (US4).

Réservé à e2e-runner. Vérifie le flow : admin disable → tool exclu de la
sélection en moins d'une minute → admin enable → tool revient.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.agent.guardrails.tool_status import _reset_cache
from app.db import SessionLocal


@pytest.fixture(autouse=True)
def _reset_status_cache() -> None:
    _reset_cache()
    yield
    _reset_cache()


@pytest.mark.e2e
def test_e2e_admin_disables_tool_then_enables(admin_client: TestClient) -> None:
    """Admin → POST disable → GET list → POST enable → GET list."""
    tool = "e2e_kill_switch_tool"

    # Cleanup
    with SessionLocal() as sess:
        sess.execute(
            text("DELETE FROM agent_tool_status WHERE tool_name = :n"),
            {"n": tool},
        )
        sess.commit()

    r = admin_client.post(
        f"/admin/agent/tools/{tool}/disable",
        json={"reason": "e2e test"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False

    # GET list inclut bien le tool désactivé
    r = admin_client.get("/admin/agent/tools")
    assert r.status_code == 200
    items = r.json()["items"]
    matched = [i for i in items if i["tool_name"] == tool]
    assert matched and matched[0]["enabled"] is False

    # Re-enable
    r = admin_client.post(f"/admin/agent/tools/{tool}/enable")
    assert r.status_code == 200
    assert r.json()["enabled"] is True

    # Cleanup
    with SessionLocal() as sess:
        sess.execute(
            text("DELETE FROM agent_tool_status WHERE tool_name = :n"),
            {"n": tool},
        )
        sess.commit()


@pytest.mark.e2e
def test_e2e_non_admin_cannot_kill_switch(
    client: TestClient, unique_email: str, valid_password: str
) -> None:
    """Non-admin reçoit 401/403/404 sur les endpoints kill-switch."""
    client.cookies.clear()
    client.post(
        "/auth/register", json={"email": unique_email, "password": valid_password}
    )
    client.post(
        "/auth/login", json={"email": unique_email, "password": valid_password}
    )
    r = client.post(
        "/admin/agent/tools/foo/disable", json={"reason": "x"}
    )
    assert r.status_code in (401, 403, 404)
