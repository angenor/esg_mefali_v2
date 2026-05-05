"""F52 US2 — Tests d'intégration changement d'e-mail."""

from __future__ import annotations

import uuid

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email, password) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client.get("/me").json()


def _engine_session():
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    return sessionmaker(bind=get_engine_migrator(), future=True)


@requires_db
class TestEmailChange:
    def test_request_creates_pending(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        new_email = f"new_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post(
            "/me/email-change",
            json={"new_email": new_email, "current_password": valid_password},
        )
        assert r.status_code == 202, r.text
        assert r.json()["email_pending"] == new_email

    def test_request_rejects_wrong_password(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post(
            "/me/email-change",
            json={
                "new_email": f"new_{uuid.uuid4().hex[:6]}@example.com",
                "current_password": "WrongPassword!1",
            },
        )
        assert r.status_code == 401

    def test_request_rejects_collision(
        self, client, unique_email, valid_password
    ) -> None:
        # Crée un autre compte d'abord
        other_email = f"itest_other_{uuid.uuid4().hex[:6]}@example.com"
        client.post(
            "/auth/register",
            json={"email": other_email, "password": valid_password},
        )
        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)
        _register_pme(client, unique_email, valid_password)

        r = client.post(
            "/me/email-change",
            json={"new_email": other_email, "current_password": valid_password},
        )
        assert r.status_code == 409
