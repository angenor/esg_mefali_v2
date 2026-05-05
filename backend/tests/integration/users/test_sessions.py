"""F52 US2 — Tests d'intégration sessions actives + révocation."""

from __future__ import annotations

import uuid

from tests.integration.conftest import requires_db


def _register_pme(client, email, password) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client.get("/me").json()


@requires_db
class TestSessions:
    def test_list_returns_at_least_one(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/sessions")
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 1
        # Au moins une session courante
        assert any(it["is_current"] for it in items)

    def test_revoke_current_session_rejected(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        items = client.get("/me/sessions").json()["items"]
        current = next(it for it in items if it["is_current"])
        r = client.delete(f"/me/sessions/{current['id']}")
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "cannot_revoke_current"

    def test_revoke_unknown_session_404(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.delete(f"/me/sessions/{uuid.uuid4()}")
        assert r.status_code == 404
