"""F06 T024-T025 — Publish workflow: 422 missing sources, 200 verified."""

from __future__ import annotations

from sqlalchemy import text

from app.db import SessionLocal
from tests.integration.conftest import requires_db


def _create_demo(client, source_id: str) -> dict:
    r = client.post(
        "/admin/demo_indicator/",
        json={
            "name": "CO2 émissions secteur agricole",
            "publisher": "ADEME",
            "external_id": f"CO2-AGRI-{source_id[:8]}",
            "description": "Émissions par hectare",
            "unit": "kgCO2/ha",
            "source_id": source_id,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@requires_db
class TestPublishFlow:
    def test_publish_pending_source_returns_422(self, admin_client, pending_source):
        obj = _create_demo(admin_client, pending_source["id"])
        r = admin_client.post(
            f"/admin/demo_indicator/{obj['id']}/publish",
            headers={"If-Match": '"v1"'},
        )
        assert r.status_code == 422
        body = r.json()["detail"]
        assert body["code"] == "sources_not_verified"
        assert len(body["missing_sources"]) == 1
        assert body["missing_sources"][0]["status"] == "pending"

    def test_publish_verified_source_returns_200(self, admin_client, verified_source):
        obj = _create_demo(admin_client, verified_source["id"])
        r = admin_client.post(
            f"/admin/demo_indicator/{obj['id']}/publish",
            headers={"If-Match": '"v1"'},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "published"
        assert body["published_by"] is not None
        assert r.headers.get("ETag") == '"v1"'

        # Verify audit_log entry written with source_of_change='admin'.
        db = SessionLocal()
        try:
            db.execute(text("SET LOCAL app.is_admin = 'true'"))
            rows = db.execute(
                text(
                    "SELECT field, source_of_change FROM audit_log "
                    "WHERE entity_type='demo_indicator' AND entity_id=CAST(:eid AS UUID)"
                ),
                {"eid": obj["id"]},
            ).all()
            actions = {r._mapping["field"] for r in rows}
            assert "create" in actions
            assert "publish" in actions
            assert all(r._mapping["source_of_change"] == "admin" for r in rows)
        finally:
            db.close()

    def test_publish_already_published_returns_409(self, admin_client, verified_source):
        obj = _create_demo(admin_client, verified_source["id"])
        admin_client.post(
            f"/admin/demo_indicator/{obj['id']}/publish",
            headers={"If-Match": '"v1"'},
        )
        r = admin_client.post(
            f"/admin/demo_indicator/{obj['id']}/publish",
            headers={"If-Match": '"v1"'},
        )
        assert r.status_code == 409
