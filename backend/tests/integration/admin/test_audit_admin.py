"""F06 T045 — admin audit: 3 mutations → 3 audit_log rows with source_of_change='admin'."""

from __future__ import annotations

from sqlalchemy import text

from app.db import SessionLocal
from tests.integration.conftest import requires_db


@requires_db
class TestAuditAdmin:
    def test_create_update_publish_emit_three_audit_rows(
        self, admin_client, verified_source
    ):
        # 1. CREATE
        r = admin_client.post(
            "/admin/demo_indicator/",
            json={
                "name": "Audited",
                "publisher": "ACME",
                "external_id": f"AUD-{verified_source['id'][:8]}",
                "source_id": verified_source["id"],
            },
        )
        assert r.status_code == 201
        eid = r.json()["id"]

        # 2. UPDATE (draft, in-place)
        r2 = admin_client.put(
            f"/admin/demo_indicator/{eid}",
            headers={"If-Match": '"v1"'},
            json={"name": "Audited v1.1"},
        )
        assert r2.status_code == 200

        # 3. PUBLISH
        r3 = admin_client.post(
            f"/admin/demo_indicator/{eid}/publish",
            headers={"If-Match": '"v1"'},
        )
        assert r3.status_code == 200

        # Verify exactly 3 audit_log rows for this entity, all source='admin'
        db = SessionLocal()
        try:
            db.execute(text("SET LOCAL app.is_admin = 'true'"))
            rows = db.execute(
                text(
                    "SELECT field, source_of_change, user_id FROM audit_log "
                    "WHERE entity_type='demo_indicator' AND entity_id=CAST(:eid AS UUID) "
                    "ORDER BY timestamp ASC"
                ),
                {"eid": eid},
            ).all()
            assert len(rows) == 3
            actions = [r._mapping["field"] for r in rows]
            assert actions == ["create", "update", "publish"]
            assert all(r._mapping["source_of_change"] == "admin" for r in rows)
            # All rows reference a user_id (the admin)
            assert all(r._mapping["user_id"] is not None for r in rows)
        finally:
            db.close()
