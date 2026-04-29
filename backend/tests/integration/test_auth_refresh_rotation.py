"""T053 — Test integration /auth/refresh rotation + détection vol."""

from __future__ import annotations

from tests.integration.conftest import requires_db


@requires_db
class TestRefreshRotation:
    def test_refresh_rotation_ok(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        old_rt = client.cookies.get("mefali_rt")
        csrf = client.cookies.get("mefali_csrf")
        r = client.post("/auth/refresh", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        new_rt = client.cookies.get("mefali_rt")
        assert new_rt != old_rt

    def test_refresh_reuse_detected(self, client, unique_email, valid_password):
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        old_rt = client.cookies.get("mefali_rt")
        csrf = client.cookies.get("mefali_csrf")
        # rotation normale
        r1 = client.post("/auth/refresh", headers={"X-CSRF-Token": csrf})
        assert r1.status_code == 200
        # nouveau csrf après rotation
        new_csrf = client.cookies.get("mefali_csrf")
        # rejouer l'ancien token : doit échouer (401)
        client.cookies.set("mefali_rt", old_rt)
        r2 = client.post("/auth/refresh", headers={"X-CSRF-Token": new_csrf})
        assert r2.status_code == 401
