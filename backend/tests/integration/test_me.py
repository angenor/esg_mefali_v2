"""T021 — Tests integration /me après register."""

from __future__ import annotations

from tests.integration.conftest import requires_db


@requires_db
class TestMe:
    def test_me_after_register(self, client, unique_email, valid_password):
        client.post(
            "/auth/register", json={"email": unique_email, "password": valid_password}
        )
        r = client.get("/me")
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == unique_email
        assert "password_hash" not in body
        assert body["role"] == "pme"

    def test_me_without_auth_returns_401(self, client):
        client.cookies.clear()
        r = client.get("/me")
        assert r.status_code == 401
