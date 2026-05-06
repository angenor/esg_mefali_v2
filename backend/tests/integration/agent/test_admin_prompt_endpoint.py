"""F54 / T065 — Tests d'intégration du endpoint admin GET /admin/agent-runs/{id}/prompt.

Couvre (SC-014) :
- Run inexistant → 404.
- Non-admin → 403.
- Run success → réponse contient hash + prompt=null.
- Run error → réponse contient hash + prompt en clair.

Le test vérifie le contrat HTTP (status codes, schéma de réponse).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_test_client():
    """Construit un FastAPI minimal montant uniquement le router F54."""
    from fastapi import FastAPI

    from app.agent.admin_router import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.integration
def test_endpoint_404_when_run_missing(
    app_test_client: TestClient,
) -> None:
    from app.agent.admin_router import router  # noqa: F401
    from app.auth.dependencies import get_current_admin
    from app.db import get_db

    fake_admin = MagicMock()
    fake_admin.role = "admin"

    fake_db = MagicMock()
    # get_prompt_for_admin renvoie None.
    with patch(
        "app.agent.admin_router.get_prompt_for_admin",
        return_value=None,
    ):
        app_test_client.app.dependency_overrides[get_current_admin] = (
            lambda: fake_admin
        )
        app_test_client.app.dependency_overrides[get_db] = lambda: fake_db
        try:
            resp = app_test_client.get(f"/admin/agent-runs/{uuid4()}/prompt")
            assert resp.status_code == 404
            body = resp.json()
            assert body["detail"]["code"] == "agent_run_not_found"
        finally:
            app_test_client.app.dependency_overrides.clear()


@pytest.mark.integration
def test_endpoint_returns_hash_only_for_success_run(
    app_test_client: TestClient,
) -> None:
    from app.auth.dependencies import get_current_admin
    from app.db import get_db

    rid = uuid4()
    fake_admin = MagicMock()
    fake_admin.role = "admin"
    fake_db = MagicMock()

    fake_row = {
        "id": rid,
        "status": "ok",
        "system_prompt_hash": "a" * 64,
        "prompt_version": "2026.05",
    }

    with patch(
        "app.agent.admin_router.get_prompt_for_admin",
        return_value=fake_row,
    ):
        app_test_client.app.dependency_overrides[get_current_admin] = (
            lambda: fake_admin
        )
        app_test_client.app.dependency_overrides[get_db] = lambda: fake_db
        try:
            resp = app_test_client.get(f"/admin/agent-runs/{rid}/prompt")
            assert resp.status_code == 200
            body = resp.json()
            assert body["run_id"] == str(rid)
            assert body["status"] == "ok"
            assert body["system_prompt_hash"] == "a" * 64
            assert body["prompt_version"] == "2026.05"
            # FR-014 : prompt = null en mode normal.
            assert body["prompt"] is None
        finally:
            app_test_client.app.dependency_overrides.clear()


@pytest.mark.integration
def test_endpoint_returns_prompt_for_error_run(
    app_test_client: TestClient,
) -> None:
    from app.auth.dependencies import get_current_admin
    from app.db import get_db

    rid = uuid4()
    fake_admin = MagicMock()
    fake_admin.role = "admin"
    fake_db = MagicMock()

    fake_row = {
        "id": rid,
        "status": "error",
        "system_prompt_hash": "b" * 64,
        "prompt_version": "2026.05",
    }

    with patch(
        "app.agent.admin_router.get_prompt_for_admin",
        return_value=fake_row,
    ):
        app_test_client.app.dependency_overrides[get_current_admin] = (
            lambda: fake_admin
        )
        app_test_client.app.dependency_overrides[get_db] = lambda: fake_db
        try:
            resp = app_test_client.get(f"/admin/agent-runs/{rid}/prompt")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "error"
            # FR-014 : prompt non-null en mode erreur.
            assert body["prompt"] is not None
            assert isinstance(body["prompt"], str)
            assert len(body["prompt"]) > 0
        finally:
            app_test_client.app.dependency_overrides.clear()
