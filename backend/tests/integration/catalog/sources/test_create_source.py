"""F07 — US1 : tests d'intégration création de Source.

Couvre :
- création OK (canonical_url stocké, statut ``pending``).
- canonicalisation de l'URL d'entrée (utm_* retirés, https forcé).
- détection de doublon (canonical_url + page) → 409 avec ``existing_id``.
- audit_log inscrit avec entity_type='source'.
"""

from __future__ import annotations

import time
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.catalog.sources.schemas import SourceCreate
from app.catalog.sources.service import create_source
from app.db import SessionLocal
from app.scripts.seed_admin import create_admin
from tests.integration.conftest import requires_db


@pytest.fixture()
def admin_id():
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"f07_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        db.commit()
        return a.id
    finally:
        db.close()


@requires_db
class TestCreateSource:
    def test_create_pending_returns_canonical_url(self, admin_id):
        unique_path = f"doc/{uuid.uuid4()}"
        payload = SourceCreate(
            url=f"http://WWW.Example.COM/{unique_path}/?utm_source=x",
            title="Doc test",
            publisher="ACME",
        )
        db = SessionLocal()
        try:
            db.execute(text("SET LOCAL app.is_admin = 'true'"))
            row, head_warning = create_source(
                db, payload, actor_id=admin_id, run_probe=False
            )
            db.commit()
        finally:
            db.close()

        assert row["verification_status"] == "pending"
        # canonical : https forcé, www. retiré, utm_* retiré, slash final retiré
        assert row["canonical_url"] == f"https://example.com/{unique_path}"
        assert head_warning is None  # probe désactivé

    def test_duplicate_canonical_url_raises_409(self, admin_id):
        unique_path = f"dup/{uuid.uuid4()}"
        payload = SourceCreate(
            url=f"https://example.com/{unique_path}",
            title="Doc test",
            publisher="ACME",
            page="42",
        )
        db = SessionLocal()
        try:
            db.execute(text("SET LOCAL app.is_admin = 'true'"))
            row1, _ = create_source(db, payload, actor_id=admin_id, run_probe=False)
            db.commit()

            # Doublon : même canonical_url, même page
            payload2 = SourceCreate(
                url=f"http://www.example.com/{unique_path}/?utm_source=x",
                title="Autre titre",
                publisher="ACME",
                page="42",
            )
            with pytest.raises(HTTPException) as exc:
                create_source(db, payload2, actor_id=admin_id, run_probe=False)
            assert exc.value.status_code == 409
            assert exc.value.detail["code"] == "duplicate_source"
            assert exc.value.detail["existing_id"] == str(row1["id"])
        finally:
            db.close()

    def test_different_page_not_duplicate(self, admin_id):
        unique_path = f"pages/{uuid.uuid4()}"
        url = f"https://example.com/{unique_path}"
        db = SessionLocal()
        try:
            db.execute(text("SET LOCAL app.is_admin = 'true'"))
            row1, _ = create_source(
                db,
                SourceCreate(url=url, title="t", publisher="P", page="1"),
                actor_id=admin_id,
                run_probe=False,
            )
            row2, _ = create_source(
                db,
                SourceCreate(url=url, title="t", publisher="P", page="2"),
                actor_id=admin_id,
                run_probe=False,
            )
            db.commit()
            assert row1["id"] != row2["id"]
        finally:
            db.close()

    def test_audit_log_recorded(self, admin_id):
        payload = SourceCreate(
            url=f"https://audit.example/{uuid.uuid4()}",
            title="Audit doc",
            publisher="ACME",
        )
        db = SessionLocal()
        try:
            db.execute(text("SET LOCAL app.is_admin = 'true'"))
            row, _ = create_source(db, payload, actor_id=admin_id, run_probe=False)
            db.commit()
            n = db.execute(
                text(
                    "SELECT count(*) FROM audit_log "
                    "WHERE entity_type = 'source' AND entity_id = :id"
                ),
                {"id": str(row["id"])},
            ).scalar()
            assert n is not None and n >= 1
        finally:
            db.close()
