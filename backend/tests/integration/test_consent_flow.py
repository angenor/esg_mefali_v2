"""F05 T034/T035 — Consent API contract + integration tests."""

from __future__ import annotations

from sqlalchemy import text

from tests.integration.conftest import requires_db


@requires_db
class TestConsentFlow:
    def _register_pme(self, client, email, password):
        r = client.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code in (200, 201), r.text
        csrf = client.cookies.get("mefali_csrf")
        if csrf:
            client.headers["X-CSRF-Token"] = csrf
        return r

    def test_list_consents_seeded_for_new_account(
        self, client, unique_email, valid_password
    ):
        self._register_pme(client, unique_email, valid_password)
        r = client.get("/me/consentements")
        assert r.status_code == 200, r.text
        data = r.json()
        kinds = {row["consent_kind"] for row in data}
        assert kinds == {
            "mobile_money",
            "exploitation_photos",
            "public_attestation",
            "long_history",
            "marketing",
        }
        # All non-essential consents start at given=false.
        assert all(row["given"] is False for row in data)

    def test_toggle_consent_on(self, client, unique_email, valid_password):
        self._register_pme(client, unique_email, valid_password)
        r = client.post(
            "/me/consentements/mobile_money", json={"given": True}
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["given"] is True
        assert body["consent_kind"] == "mobile_money"
        assert body["given_at"] is not None
        # Audit log must record the change. Use migrator engine (BYPASS RLS).
        from sqlalchemy.orm import sessionmaker

        from app.db import get_engine_migrator

        Sess = sessionmaker(bind=get_engine_migrator(), future=True)
        with Sess() as s:
            cnt = s.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log WHERE entity_type='consent' "
                    "AND field='consent_kind' AND new_value->>'given' = 'true'"
                )
            ).scalar()
            assert cnt is not None and cnt >= 1

    def test_toggle_consent_off_then_on(self, client, unique_email, valid_password):
        self._register_pme(client, unique_email, valid_password)
        client.post("/me/consentements/marketing", json={"given": True})
        r2 = client.post("/me/consentements/marketing", json={"given": False})
        assert r2.status_code == 200
        assert r2.json()["given"] is False
        assert r2.json()["withdrawn_at"] is not None

    def test_toggle_consent_unknown_kind_422(
        self, client, unique_email, valid_password
    ):
        self._register_pme(client, unique_email, valid_password)
        r = client.post("/me/consentements/__bogus__", json={"given": True})
        assert r.status_code == 422

    def test_consents_unauth_401(self, client):
        client.cookies.clear()
        r = client.get("/me/consentements")
        assert r.status_code == 401

    def test_toggle_payload_extra_field_rejected(
        self, client, unique_email, valid_password
    ):
        self._register_pme(client, unique_email, valid_password)
        r = client.post(
            "/me/consentements/long_history",
            json={"given": True, "rogue": "field"},
        )
        assert r.status_code == 422
