"""F09 T091 — Audit chain : create → publish → modify (v2 draft) → audit logs."""

from __future__ import annotations

import uuid

from sqlalchemy import text

from app.db import SessionLocal
from tests.integration.conftest import requires_db


@requires_db
def test_audit_versioning_chain(admin_client, verified_source):
    code = f"AUDIT_{uuid.uuid4().hex[:6].upper()}"
    r = admin_client.post(
        "/admin/indicateurs/",
        json={
            "code": code,
            "name": "audit",
            "definition": "x",
            "pillar": "E",
            "unite": "kg",
            "value_type": "numeric",
            "source_ids": [verified_source["id"]],
        },
    )
    obj = r.json()
    admin_client.post(
        f"/admin/indicateurs/{obj['id']}/publish", headers={"If-Match": '"v1"'}
    )
    r3 = admin_client.patch(
        f"/admin/indicateurs/{obj['id']}",
        json={"name": "v2"},
        headers={"If-Match": '"v1"'},
    )
    assert r3.status_code == 200
    new_id = r3.json()["id"]

    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        rows = db.execute(
            text(
                "SELECT field FROM audit_log "
                "WHERE entity_type='indicateur' "
                "AND entity_id IN (CAST(:a AS UUID), CAST(:b AS UUID))"
            ),
            {"a": obj["id"], "b": new_id},
        ).all()
        actions = {r._mapping["field"] for r in rows}
        # Expect at least create, publish, new_version (or update).
        assert "create" in actions
        assert "publish" in actions
        assert "new_version" in actions or "update" in actions
    finally:
        db.close()
