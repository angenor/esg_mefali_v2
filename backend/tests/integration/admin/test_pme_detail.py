"""F10 US1+US2 T022/T031 — Integration tests for ``GET /admin/pme/{id}``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from tests.integration.conftest import requires_db


def _create_pme_account(name: str = "Test PME") -> uuid.UUID:
    """Insert one ``account`` row directly (admin-context bypass)."""
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        aid = uuid.uuid4()
        now = datetime.now(tz=UTC)
        db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (CAST(:id AS UUID), :name, :now, :now)"
            ),
            {"id": str(aid), "name": name, "now": now},
        )
        db.commit()
        return aid
    finally:
        db.close()


def _count_admin_view_audits(account_id: uuid.UUID, section: str) -> int:
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        n = db.execute(
            text(
                "SELECT count(*) FROM audit_log "
                "WHERE entity_type='admin_view' AND entity_id = CAST(:id AS UUID) "
                "AND field = :f AND source_of_change = 'admin'"
            ),
            {"id": str(account_id), "f": f"section.{section}"},
        ).scalar()
        return int(n or 0)
    finally:
        db.close()


@requires_db
def test_get_pme_detail_404_when_unknown(admin_client: TestClient) -> None:
    fake = uuid.uuid4()
    r = admin_client.get(f"/admin/pme/{fake}")
    assert r.status_code == 404, r.text


@requires_db
def test_get_pme_detail_emits_admin_view_audit(admin_client: TestClient) -> None:
    aid = _create_pme_account("PME audit test")
    r = admin_client.get(f"/admin/pme/{aid}?section=projets")
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["section"] == "projets"
    assert payload["account"]["id"] == str(aid)
    assert _count_admin_view_audits(aid, "projets") >= 1


@requires_db
def test_get_pme_detail_invalid_section_422(admin_client: TestClient) -> None:
    aid = _create_pme_account("PME section test")
    r = admin_client.get(f"/admin/pme/{aid}?section=hacked")
    assert r.status_code == 422, r.text


@requires_db
def test_get_pme_detail_pme_user_forbidden(pme_client: TestClient) -> None:
    fake = uuid.uuid4()
    r = pme_client.get(f"/admin/pme/{fake}")
    assert r.status_code == 403, r.text
