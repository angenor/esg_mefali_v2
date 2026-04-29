"""F03 US6 — RLS test : un tenant ne voit pas les claims d'un autre."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import text

from app.db import get_engine_migrator
from tests.integration.conftest import requires_db


def _register_pme(client, valid_password):
    client.cookies.clear()
    email = f"rls_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": valid_password})
    assert r.status_code == 201, r.text
    body = r.json()
    return body["account_id"], body["user_id"], email


@requires_db
class TestRlsUnsourced:
    def test_tenant_isolation(self, client, valid_password):
        # Tenant A
        acc_a, user_a, _ = _register_pme(client, valid_password)
        # Tenant B
        acc_b, user_b, email_b = _register_pme(client, valid_password)

        # Insère 1 claim pour A et 1 claim pour B (via migrator)
        eng = get_engine_migrator()
        with eng.begin() as c:
            for aid, uid, txt in (
                (acc_a, user_a, "claim tenant A"),
                (acc_b, user_b, "claim tenant B"),
            ):
                c.execute(
                    text(
                        "INSERT INTO unsourced_claim_log "
                        "(id, account_id, user_id, claim_text) "
                        "VALUES (:id, :aid, :uid, :c)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "aid": aid,
                        "uid": uid,
                        "c": txt,
                    },
                )

        # Re-login B pour avoir le contexte tenant B
        client.cookies.clear()
        r = client.post(
            "/auth/login", json={"email": email_b, "password": valid_password}
        )
        assert r.status_code == 200, r.text
        csrf = client.cookies.get("mefali_csrf")
        client.headers["x-csrf-token"] = csrf or ""

        r = client.get("/admin/unsourced-claims?days=30")
        assert r.status_code == 200
        body = r.json()
        # B ne doit voir que son propre claim
        claims = {row["claim"] for row in body}
        assert "claim tenant b" in claims
        assert "claim tenant a" not in claims
