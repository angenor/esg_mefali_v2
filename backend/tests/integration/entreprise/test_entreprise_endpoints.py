"""F11 — Tests integration endpoints /me/entreprise (US1, US2, US5, US6)."""

from __future__ import annotations

import time
import uuid as _uuid

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email: str, password: str) -> None:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


@requires_db
class TestEntrepriseGet:
    def test_get_provisions_profile_for_new_account(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/entreprise")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["version"] == 1
        assert body["account_id"]
        assert body["taille_effectifs"] is None
        assert body["secteur_code"] is None

    def test_get_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get("/me/entreprise")
        assert r.status_code == 401


@requires_db
class TestEntreprisePatch:
    def test_patch_sets_effectifs_and_increments_version(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/entreprise")
        r = client.patch(
            "/me/entreprise",
            json={"taille_effectifs": 75},
            headers={"If-Match": "1"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["taille_effectifs"] == 75
        assert body["version"] == 2

    def test_patch_secteur_sets_label(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/entreprise")
        r = client.patch(
            "/me/entreprise",
            json={"secteur_code": "agro_elevage"},
            headers={"If-Match": "1"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["secteur_code"] == "agro_elevage"
        assert body["secteur_label"] and "Élevage" in body["secteur_label"]

    def test_patch_money_ok(self, client, unique_email, valid_password) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/entreprise")
        r = client.patch(
            "/me/entreprise",
            json={"taille_ca": {"amount": "250000000", "currency": "XOF"}},
            headers={"If-Match": "1"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["taille_ca"]["currency"] == "XOF"

    def test_patch_invalid_secteur_returns_422(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/entreprise")
        r = client.patch(
            "/me/entreprise",
            json={"secteur_code": "fake_sector"},
            headers={"If-Match": "1"},
        )
        assert r.status_code == 422

    def test_patch_without_ifmatch_returns_428(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/entreprise")
        r = client.patch("/me/entreprise", json={"taille_effectifs": 5})
        assert r.status_code == 428

    def test_patch_stale_version_returns_409(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/entreprise")
        r1 = client.patch(
            "/me/entreprise",
            json={"taille_effectifs": 10},
            headers={"If-Match": "1"},
        )
        assert r1.status_code == 200
        r2 = client.patch(
            "/me/entreprise",
            json={"taille_effectifs": 20},
            headers={"If-Match": "1"},
        )
        assert r2.status_code == 409
        body = r2.json()
        detail = body.get("detail", body)
        assert detail.get("code") == "version_conflict"
        assert detail.get("current_version") == 2
        assert detail.get("your_version") == 1


@requires_db
class TestEntrepriseAuditTrail:
    def test_patch_records_audit_per_field(
        self, client, unique_email, valid_password, db_engine
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/entreprise")
        r = client.patch(
            "/me/entreprise",
            json={
                "taille_effectifs": 50,
                "secteur_code": "fintech",
                "localisation_siege_pays_iso2": "CI",
            },
            headers={"If-Match": "1"},
        )
        assert r.status_code == 200, r.text
        ent_id = r.json()["id"]

        with db_engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT field, source_of_change FROM audit_log
                    WHERE entity_type = 'entreprise'
                      AND entity_id = CAST(:eid AS UUID)
                      AND field IS NOT NULL
                    """
                ),
                {"eid": ent_id},
            ).fetchall()

        fields = {r[0] for r in rows}
        assert "taille_effectifs" in fields
        assert "secteur_code" in fields
        assert "localisation_siege_pays_iso2" in fields
        for r2 in rows:
            assert str(r2[1]) == "manual"


@requires_db
class TestEntrepriseSectors:
    def test_sectors_endpoint_returns_list(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/entreprise/sectors")
        assert r.status_code == 200
        body = r.json()
        assert len(body) >= 30
        assert {"code", "label"} <= set(body[0].keys())


@requires_db
class TestEntrepriseCompleteness:
    def test_completeness_zero_then_partial(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/entreprise")
        r = client.get("/me/entreprise/completeness")
        assert r.status_code == 200
        body = r.json()
        assert body["percentage"] == 0
        codes = {f["feature_code"] for f in body["missing_required_for_features"]}
        assert "esg_scoring" in codes
        client.patch(
            "/me/entreprise",
            json={
                "secteur_code": "fintech",
                "taille_effectifs": 12,
                "taille_ca": {"amount": "1000000", "currency": "XOF"},
            },
            headers={"If-Match": "1"},
        )
        r = client.get("/me/entreprise/completeness")
        body = r.json()
        esg = next(
            f for f in body["missing_required_for_features"]
            if f["feature_code"] == "esg_scoring"
        )
        assert esg["missing_fields"] == []


@requires_db
class TestEntrepriseRLS:
    def test_two_accounts_dont_see_each_other(self, client, valid_password) -> None:
        e1 = f"a_{int(time.time()*1000)}_{_uuid.uuid4().hex[:6]}@example.com"
        e2 = f"b_{int(time.time()*1000)}_{_uuid.uuid4().hex[:6]}@example.com"
        _register_pme(client, e1, valid_password)
        client.get("/me/entreprise")
        r1 = client.patch(
            "/me/entreprise",
            json={"taille_effectifs": 11},
            headers={"If-Match": "1"},
        )
        assert r1.status_code == 200
        ent_a = r1.json()["id"]
        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)
        _register_pme(client, e2, valid_password)
        rb = client.get("/me/entreprise")
        assert rb.status_code == 200
        assert rb.json()["id"] != ent_a
        assert rb.json()["taille_effectifs"] is None
