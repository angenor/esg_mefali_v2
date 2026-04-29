"""F09 T004 — RLS catalogue F09 : admin voit draft+published, pme voit published."""

from __future__ import annotations

import uuid

from sqlalchemy import text

from app.db import SessionLocal
from tests.integration.conftest import requires_db


@requires_db
def test_pme_session_only_sees_published_indicateurs(admin_client, verified_source):
    # Create a draft + a published indicateur.
    draft = admin_client.post(
        "/admin/indicateurs/",
        json={
            "code": f"RLS_D_{uuid.uuid4().hex[:4].upper()}",
            "name": "draft",
            "definition": "x",
            "pillar": "E",
            "unite": "kg",
            "value_type": "numeric",
            "source_ids": [verified_source["id"]],
        },
    ).json()
    pub = admin_client.post(
        "/admin/indicateurs/",
        json={
            "code": f"RLS_P_{uuid.uuid4().hex[:4].upper()}",
            "name": "pub",
            "definition": "x",
            "pillar": "E",
            "unite": "kg",
            "value_type": "numeric",
            "source_ids": [verified_source["id"]],
        },
    ).json()
    admin_client.post(
        f"/admin/indicateurs/{pub['id']}/publish", headers={"If-Match": '"v1"'}
    )

    # Admin context: voit les deux.
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        rows = db.execute(
            text("SELECT status FROM indicateur WHERE id IN (CAST(:a AS UUID), CAST(:b AS UUID))"),
            {"a": draft["id"], "b": pub["id"]},
        ).all()
        statuses = {r[0] for r in rows}
        assert statuses == {"draft", "published"}
    finally:
        db.close()

    # PME context: ne voit que published.
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'false'"))
        rows = db.execute(
            text("SELECT status FROM indicateur WHERE id IN (CAST(:a AS UUID), CAST(:b AS UUID))"),
            {"a": draft["id"], "b": pub["id"]},
        ).all()
        statuses = {r[0] for r in rows}
        assert statuses == {"published"}
    finally:
        db.close()
