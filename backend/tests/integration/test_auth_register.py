"""T020 — Tests integration /auth/register."""

from __future__ import annotations

from tests.integration.conftest import requires_db


@requires_db
class TestRegister:
    def test_register_success(self, client, unique_email, valid_password):
        r = client.post(
            "/auth/register", json={"email": unique_email, "password": valid_password}
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["email"] == unique_email
        assert body["role"] == "pme"
        assert body["account_id"] is not None
        assert "password_hash" not in body
        # cookies positionnés
        assert "mefali_at" in client.cookies
        assert "mefali_rt" in client.cookies
        assert "mefali_csrf" in client.cookies

    def test_register_duplicate_email_returns_409(
        self, client, unique_email, valid_password
    ):
        r1 = client.post(
            "/auth/register", json={"email": unique_email, "password": valid_password}
        )
        assert r1.status_code == 201
        # second fresh client (sinon cookies existant gênent)
        client.cookies.clear()
        r2 = client.post(
            "/auth/register", json={"email": unique_email, "password": valid_password}
        )
        assert r2.status_code == 409
        assert r2.json()["detail"]["code"] == "email_already_used"

    def test_register_weak_password_returns_422(self, client, unique_email):
        r = client.post(
            "/auth/register", json={"email": unique_email, "password": "weak"}
        )
        assert r.status_code == 422

    def test_register_invalid_email_returns_422(self, client, valid_password):
        r = client.post(
            "/auth/register", json={"email": "not-an-email", "password": valid_password}
        )
        assert r.status_code == 422
