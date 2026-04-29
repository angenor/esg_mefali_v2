"""F09 T064 — Auto-clôture du valid_to_date à l'insertion v2."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import text

from app.db import SessionLocal
from tests.integration.conftest import requires_db


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4].upper()}"


@requires_db
def test_inserting_v2_closes_v1_valid_to(admin_client, verified_source):
    code = _uniq("V2")
    # v1 — 2024-01-01 NULL
    p1 = {
        "code": code,
        "name": "v1",
        "valeur": "0.10",
        "unite": "kgCO2e",
        "pays_iso2": "CI",
        "scope": "1",
        "categorie": "energie",
        "source_id": verified_source["id"],
        "valid_from_date": "2024-01-01",
    }
    r1 = admin_client.post("/admin/facteurs-emission/", json=p1)
    assert r1.status_code == 201
    # v2 — 2025-01-01 (must close v1).
    p2 = {**p1, "name": "v2", "valeur": "0.08", "valid_from_date": "2025-01-01"}
    r2 = admin_client.post("/admin/facteurs-emission/", json=p2)
    assert r2.status_code == 201, r2.text
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        rows = db.execute(
            text(
                "SELECT name, valid_from_date, valid_to_date FROM facteur_emission "
                "WHERE code = :c AND pays_iso2 = 'CI' "
                "ORDER BY valid_from_date"
            ),
            {"c": code},
        ).all()
        assert len(rows) == 2
        # v1 should now have valid_to_date = 2024-12-31.
        assert str(rows[0]._mapping["valid_to_date"]) == "2024-12-31"
        # v2 still open.
        assert rows[1]._mapping["valid_to_date"] is None
    finally:
        db.close()
