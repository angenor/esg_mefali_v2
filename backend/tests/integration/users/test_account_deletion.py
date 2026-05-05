"""F52 US2 — Tests d'intégration ``/me/account-deletion``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

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


def _seed_entreprise(account_id: str, raison_sociale: str) -> None:
    sess = _engine_session()
    with sess() as s:
        now = datetime.now(UTC).replace(tzinfo=None)
        s.execute(
            text(
                """
                INSERT INTO entreprise
                  (id, account_id, name, version, created_at, updated_at)
                VALUES
                  (gen_random_uuid(), CAST(:aid AS UUID), :rs, 1, :ts, :ts)
                """
            ),
            {"aid": account_id, "rs": raison_sociale, "ts": now},
        )
        s.commit()


@requires_db
class TestAccountDeletion:
    def test_get_no_pending_initial(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/account-deletion")
        assert r.status_code == 200
        assert r.json()["request"] is None

    def test_create_with_correct_raison_sociale(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        _seed_entreprise(me["account_id"], "ACME SARL")
        r = client.post(
            "/me/account-deletion",
            json={
                "confirmation_text": "ACME SARL",
                "reason_motif": "test",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()["request"]
        assert body["status"] == "pending"
        # scheduled_for ≈ +30j
        scheduled = datetime.fromisoformat(body["scheduled_for"].replace("Z", "+00:00"))
        delta = scheduled - datetime.now(UTC)
        assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)

    def test_create_with_wrong_text_400(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        _seed_entreprise(me["account_id"], "ACME SARL")
        r = client.post(
            "/me/account-deletion",
            json={"confirmation_text": "WRONG"},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "confirmation_mismatch"

    def test_double_create_409(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        _seed_entreprise(me["account_id"], "ACME SARL")
        r1 = client.post(
            "/me/account-deletion", json={"confirmation_text": "ACME SARL"}
        )
        assert r1.status_code == 201
        r2 = client.post(
            "/me/account-deletion", json={"confirmation_text": "ACME SARL"}
        )
        assert r2.status_code == 409

    def test_cancel_pending(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        _seed_entreprise(me["account_id"], "ACME SARL")
        rid = client.post(
            "/me/account-deletion", json={"confirmation_text": "ACME SARL"}
        ).json()["request"]["id"]
        r = client.delete(f"/me/account-deletion/{rid}")
        assert r.status_code == 204
        # plus de pending
        r2 = client.get("/me/account-deletion")
        assert r2.json()["request"] is None

    def test_cancel_unknown_404(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.delete(f"/me/account-deletion/{uuid.uuid4()}")
        assert r.status_code == 404
