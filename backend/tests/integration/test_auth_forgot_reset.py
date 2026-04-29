"""T057 — Tests integration /auth/forgot-password + /auth/reset-password."""

from __future__ import annotations

from app.auth.service import (
    request_password_reset,
)
from app.db import SessionLocal
from tests.integration.conftest import requires_db


@requires_db
class TestForgotReset:
    def test_forgot_unknown_email_neutral_202(self, client):
        client.cookies.clear()
        r = client.post(
            "/auth/forgot-password", json={"email": "noone_zzz@example.com"}
        )
        assert r.status_code == 202
        assert r.json() == {"status": "accepted"}

    def test_forgot_known_email_neutral_202(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        client.cookies.clear()
        r = client.post("/auth/forgot-password", json={"email": unique_email})
        assert r.status_code == 202
        assert r.json() == {"status": "accepted"}

    def test_reset_full_cycle(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        # On récupère le token via le service (test : on n'a pas l'email)
        db = SessionLocal()
        try:
            token = request_password_reset(db, email=unique_email)
            db.commit()
        finally:
            db.close()
        assert token is not None

        client.cookies.clear()
        r = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "AnotherSafe!Pass99"},
        )
        assert r.status_code == 204

        # nouveau mdp fonctionne
        r2 = client.post(
            "/auth/login",
            json={"email": unique_email, "password": "AnotherSafe!Pass99"},
        )
        assert r2.status_code == 200

        # reuse refusé
        r3 = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "ThirdPass!2025"},
        )
        assert r3.status_code == 400
