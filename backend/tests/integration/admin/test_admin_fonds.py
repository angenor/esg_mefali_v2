"""F08 US1 — tests Fonds source CRUD + publish gate + ETag + audit."""

from __future__ import annotations

from sqlalchemy import text

from app.db import SessionLocal
from tests.integration.conftest import requires_db


def _payload(source_id: str, *, name: str = "GCF") -> dict:
    return {
        "name": name,
        "organisation": "Green Climate Fund",
        "type": "multilateral",
        "thematique": ["climat"],
        "instruments": ["don"],
        "eligibilite_geo": ["CI", "SN"],
        "submission_mode": "rolling",
        "criteres_json": [],
        "documents_requis_json": [],
        "frais_json": {},
        "delais_json": {},
        "source_ids": [source_id],
    }


@requires_db
class TestFondsAdminCRUD:
    def test_create_draft_returns_201(self, admin_client, verified_source):
        r = admin_client.post("/admin/fonds/", json=_payload(verified_source["id"]))
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "draft"
        assert body["organisation"] == "Green Climate Fund"
        assert r.headers.get("ETag") == '"v1"'

    def test_publish_requires_verified_source(self, admin_client, pending_source):
        r = admin_client.post("/admin/fonds/", json=_payload(pending_source["id"]))
        obj = r.json()
        r2 = admin_client.post(
            f"/admin/fonds/{obj['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r2.status_code == 422
        assert r2.json()["detail"]["code"] == "sources_not_verified"

    def test_publish_with_verified_source_succeeds(self, admin_client, verified_source):
        r = admin_client.post("/admin/fonds/", json=_payload(verified_source["id"], name="GCF-pub"))
        obj = r.json()
        r2 = admin_client.post(
            f"/admin/fonds/{obj['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "published"

    def test_etag_mismatch_returns_412(self, admin_client, verified_source):
        r = admin_client.post("/admin/fonds/", json=_payload(verified_source["id"], name="GCF-etag"))
        obj = r.json()
        r2 = admin_client.put(
            f"/admin/fonds/{obj['id']}",
            json={"name": "GCF-renamed"},
            headers={"If-Match": '"v9"'},
        )
        assert r2.status_code == 412

    def test_audit_log_records_diff(self, admin_client, verified_source):
        r = admin_client.post("/admin/fonds/", json=_payload(verified_source["id"], name="GCF-audit"))
        obj = r.json()
        admin_client.post(f"/admin/fonds/{obj['id']}/publish", headers={"If-Match": '"v1"'})
        db = SessionLocal()
        try:
            db.execute(text("SET LOCAL app.is_admin = 'true'"))
            rows = db.execute(
                text(
                    "SELECT field FROM audit_log "
                    "WHERE entity_type='fonds_source' AND entity_id=CAST(:eid AS UUID)"
                ),
                {"eid": obj["id"]},
            ).all()
            actions = {r._mapping["field"] for r in rows}
            assert "create" in actions
            assert "publish" in actions
        finally:
            db.close()

    def test_deadline_required_for_call_for_proposals(self, admin_client, verified_source):
        body = _payload(verified_source["id"], name="GCF-cfp")
        body["submission_mode"] = "call_for_proposals"
        body["deadline"] = None
        r = admin_client.post("/admin/fonds/", json=body)
        assert r.status_code == 422
