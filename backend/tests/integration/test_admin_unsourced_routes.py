"""F03 US6 — Tests integration /admin/unsourced-claims (agrégation + tri)."""

from __future__ import annotations

import time
import uuid

import pytest
from sqlalchemy import text

from app.db import get_engine_migrator
from tests.integration.conftest import requires_db


@pytest.fixture()
def pme_with_claims(client, valid_password):
    """Crée une PME et y inscrit 5 claims dont 3 normalisables identiques."""
    email = f"pme_uns_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": valid_password})
    assert r.status_code == 201, r.text
    body = r.json()
    account_id = body["account_id"]
    user_id = body["user_id"]

    eng = get_engine_migrator()
    rows_inserted = [
        ("seuil GCF inconnu", account_id, user_id),
        ("Seuil GCF inconnu", account_id, user_id),  # même normalisé
        ("seuil gcf inconnu  ", account_id, user_id),  # même normalisé
        ("autre claim x", account_id, user_id),
        ("autre claim y", account_id, user_id),
    ]
    with eng.begin() as c:
        for claim, aid, uid in rows_inserted:
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
                    "c": claim,
                },
            )
    return account_id


@requires_db
class TestAdminUnsourcedRoutes:
    def test_aggregates_normalized_claims(self, client, pme_with_claims):
        # Le user PME courant est connecté ; RLS scope l'agrégation à son tenant.
        csrf = client.cookies.get("mefali_csrf")
        client.headers["x-csrf-token"] = csrf or ""
        r = client.get("/admin/unsourced-claims?days=30&limit=50")
        assert r.status_code == 200, r.text
        body = r.json()
        # 3 claims normalisés distincts
        assert len(body) == 3
        # Le plus fréquent (3 occurrences "seuil gcf inconnu")
        assert body[0]["claim"] == "seuil gcf inconnu"
        assert body[0]["freq"] == 3
