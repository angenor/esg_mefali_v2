"""F42 T021 — Tests intégration /me/preferences."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Generator

import pytest

os.environ.setdefault("DISABLE_RATE_LIMIT", "1")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from tests.conftest import DB_AVAILABLE  # noqa: E402

requires_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="Postgres indisponible — démarrer `docker compose up -d postgres`.",
)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def unique_email() -> str:
    return f"itest_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"


@pytest.fixture()
def valid_password() -> str:
    return "Sup3rSecret!Pass"


def _csrf(client: TestClient) -> dict[str, str]:
    csrf = client.cookies.get("mefali_csrf", "")
    return {"x-csrf-token": csrf}


@requires_db
class TestUserPreferences:
    def test_get_without_session_returns_401(self, client):
        client.cookies.clear()
        r = client.get("/me/preferences")
        assert r.status_code == 401

    def test_get_first_time_creates_pending(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        r = client.get("/me/preferences")
        assert r.status_code == 200
        body = r.json()
        assert body["onboarding_state"] == "pending"
        assert "onboarding_state_updated_at" in body

    def test_get_idempotent_no_duplicate(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        r1 = client.get("/me/preferences")
        r2 = client.get("/me/preferences")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["onboarding_state_updated_at"] == r2.json()["onboarding_state_updated_at"]

    def test_patch_completed_audit(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        client.get("/me/preferences")
        r = client.patch(
            "/me/preferences",
            json={"onboarding_state": "completed"},
            headers=_csrf(client),
        )
        assert r.status_code == 200
        assert r.json()["onboarding_state"] == "completed"

    def test_patch_invalid_value(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        r = client.patch(
            "/me/preferences",
            json={"onboarding_state": "invalid_value"},
            headers=_csrf(client),
        )
        assert r.status_code == 422

    def test_patch_extra_field_forbidden(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        r = client.patch(
            "/me/preferences",
            json={"onboarding_state": "skipped", "unknown_field": True},
            headers=_csrf(client),
        )
        assert r.status_code == 422

    def test_patch_idempotent_same_value(
        self, client, unique_email, valid_password
    ):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        client.get("/me/preferences")
        r1 = client.patch(
            "/me/preferences",
            json={"onboarding_state": "completed"},
            headers=_csrf(client),
        )
        r2 = client.patch(
            "/me/preferences",
            json={"onboarding_state": "completed"},
            headers=_csrf(client),
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["onboarding_state_updated_at"] == r2.json()["onboarding_state_updated_at"]

    def test_rls_isolation_between_tenants(
        self, client, unique_email, valid_password
    ):
        # User A
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        client.patch(
            "/me/preferences",
            json={"onboarding_state": "completed"},
            headers=_csrf(client),
        )
        client.cookies.clear()

        # User B
        emailB = f"itest_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
        client.post(
            "/auth/register",
            json={"email": emailB, "password": valid_password},
        )
        rB = client.get("/me/preferences")
        assert rB.status_code == 200
        # User B doit voir son propre 'pending', pas les données de A
        assert rB.json()["onboarding_state"] == "pending"
