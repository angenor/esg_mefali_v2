"""T032 — Tests integration /auth/login."""

from __future__ import annotations

from tests.integration.conftest import requires_db


@requires_db
class TestLogin:
    def test_login_success(self, client, unique_email, valid_password):
        client.post(
            "/auth/register", json={"email": unique_email, "password": valid_password}
        )
        client.cookies.clear()
        r = client.post(
            "/auth/login", json={"email": unique_email, "password": valid_password}
        )
        assert r.status_code == 200
        assert r.json()["email"] == unique_email
        assert "mefali_at" in client.cookies
        # last_login_at mis à jour
        assert r.json().get("last_login_at") is not None

    def test_unknown_and_bad_password_have_same_response(
        self, client, unique_email, valid_password
    ):
        client.post(
            "/auth/register", json={"email": unique_email, "password": valid_password}
        )
        client.cookies.clear()

        # cas A : mauvais mdp
        rA = client.post(
            "/auth/login", json={"email": unique_email, "password": "WrongPassword99X"}
        )
        # cas B : email inconnu
        rB = client.post(
            "/auth/login",
            json={"email": "noone_xyz_xyz@example.com", "password": "WrongPassword99X"},
        )
        assert rA.status_code == 401
        assert rB.status_code == 401
        assert rA.json() == rB.json()
        assert rA.headers.get("content-type") == rB.headers.get("content-type")
