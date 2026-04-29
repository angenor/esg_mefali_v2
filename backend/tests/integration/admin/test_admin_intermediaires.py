"""F08 US2 — tests Intermédiaire CRUD + publish."""

from __future__ import annotations

from sqlalchemy import text

from app.db import SessionLocal
from tests.integration.conftest import requires_db


def _payload(source_id: str, *, name: str = "BOAD") -> dict:
    return {
        "name": name,
        "type": "banque_locale",
        "pays": ["CI", "SN"],
        "zone_op": "UEMOA",
        "frais_json": {"origination_pct": 1.0, "currency": "EUR"},
        "delais_json": {"instruction_jours": 30},
        "criteres_json": [],
        "documents_requis_json": [],
        "source_ids": [source_id],
    }


@requires_db
class TestIntermediaireAdminCRUD:
    def test_crud_lifecycle(self, admin_client, verified_source):
        r = admin_client.post("/admin/intermediaires/", json=_payload(verified_source["id"]))
        assert r.status_code == 201, r.text
        obj = r.json()
        assert obj["status"] == "draft"
        # Read
        r2 = admin_client.get(f"/admin/intermediaires/{obj['id']}")
        assert r2.status_code == 200
        # Update
        r3 = admin_client.put(
            f"/admin/intermediaires/{obj['id']}",
            json={"zone_op": "CEDEAO"},
            headers={"If-Match": '"v1"'},
        )
        assert r3.status_code == 200
        assert r3.json()["zone_op"] == "CEDEAO"

    def test_publish_gate_and_audit(self, admin_client, verified_source, pending_source):
        # publish KO with pending source
        r = admin_client.post(
            "/admin/intermediaires/", json=_payload(pending_source["id"], name="ACME-pending")
        )
        obj = r.json()
        r2 = admin_client.post(
            f"/admin/intermediaires/{obj['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r2.status_code == 422

        # publish OK with verified
        r3 = admin_client.post(
            "/admin/intermediaires/", json=_payload(verified_source["id"], name="ACME-verified")
        )
        obj2 = r3.json()
        r4 = admin_client.post(
            f"/admin/intermediaires/{obj2['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r4.status_code == 200

        # Audit log
        db = SessionLocal()
        try:
            db.execute(text("SET LOCAL app.is_admin = 'true'"))
            rows = db.execute(
                text(
                    "SELECT field FROM audit_log "
                    "WHERE entity_type='intermediaire' AND entity_id=CAST(:eid AS UUID)"
                ),
                {"eid": obj2["id"]},
            ).all()
            actions = {r._mapping["field"] for r in rows}
            assert "create" in actions
            assert "publish" in actions
        finally:
            db.close()
