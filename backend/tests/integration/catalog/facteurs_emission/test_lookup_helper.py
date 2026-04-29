"""F09 T063 — Helper ``get_facteur`` (FR-007 + fallback pays mondial)."""

from __future__ import annotations

import time
import uuid
from datetime import date

from sqlalchemy import text

from app.catalog.facteurs_emission.lookup import get_facteur
from app.db import SessionLocal
from tests.integration.conftest import requires_db


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4].upper()}"


def _create_published(admin_client, *, code: str, valeur: str, source_id: str,
                     pays: str | None, valid_from: str = "2024-01-01") -> dict:
    payload = {
        "code": code,
        "name": f"facteur {code}",
        "valeur": valeur,
        "unite": "kgCO2e/kWh",
        "pays_iso2": pays,
        "scope": "1",
        "categorie": "energie",
        "source_id": source_id,
        "valid_from_date": valid_from,
    }
    r = admin_client.post("/admin/facteurs-emission/", json=payload)
    assert r.status_code == 201, r.text
    obj = r.json()
    pub = admin_client.post(
        f"/admin/facteurs-emission/{obj['id']}/publish", headers={"If-Match": '"v1"'}
    )
    assert pub.status_code == 200, pub.text
    return pub.json()


@requires_db
def test_lookup_resolves_country_match(admin_client, verified_source):
    code = _uniq("ELEC")
    _create_published(
        admin_client, code=code, valeur="0.05", source_id=verified_source["id"],
        pays="CI",
    )
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        row = get_facteur(db, code, pays_iso2="CI", at=date(2024, 6, 1))
        assert row is not None
        assert row["pays_iso2"] == "CI"
    finally:
        db.close()


@requires_db
def test_lookup_falls_back_to_world(admin_client, verified_source):
    code = _uniq("WORLD")
    # Only world facteur (pays=NULL).
    _create_published(
        admin_client, code=code, valeur="0.40",
        source_id=verified_source["id"], pays=None,
    )
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        row = get_facteur(db, code, pays_iso2="CI", at=date(2024, 6, 1))
        assert row is not None
        assert row["pays_iso2"] is None  # world
    finally:
        db.close()


@requires_db
def test_lookup_404_when_no_match(admin_client, verified_source):
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        row = get_facteur(db, "DOES_NOT_EXIST", pays_iso2="CI")
        assert row is None
    finally:
        db.close()
