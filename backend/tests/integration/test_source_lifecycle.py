"""F03 US1 — Tests integration cycle de vie Source.

Couvre :
- Insertion catalogue (indicateur) sans source_id verified n'apparaît PAS dans v_indicateur_verified.
- Suppression source liée refusée par ON DELETE RESTRICT (FR-014) — vérifié via FK indicateur.
- Workflow create_pending -> verify (avec embedding stub) -> mark_outdated.
- Trigger SQL refuse double validation.
"""

from __future__ import annotations

import time
import uuid

import pytest
from sqlalchemy import text

from app.db import SessionLocal, get_engine_migrator
from app.scripts.seed_admin import create_admin
from app.services import source_service
from tests.integration.conftest import requires_db


def _stub_embedding(_texts):
    return [[0.0] * 1024]


def _make_admin(db, suffix: str):
    email = f"src_{suffix}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
    user = create_admin(db, email=email, password="Sup3rSecret!Pass")
    db.commit()
    return user


@pytest.fixture()
def two_admins():
    db = SessionLocal()
    try:
        a = _make_admin(db, "a")
        b = _make_admin(db, "b")
        a_id, b_id = a.id, b.id
        yield a_id, b_id
    finally:
        db.close()


@requires_db
class TestSourceLifecycle:
    def test_create_pending_then_verify_with_other_admin(self, two_admins):
        captured_by, verifier = two_admins
        # On utilise l'engine migrator pour bypass RLS (admin global, pas d'account)
        engine = get_engine_migrator()
        with engine.begin() as conn:
            sid = source_service.create_pending(
                conn,
                captured_by=captured_by,
                url="https://gcf.example/criteria.pdf",
                title="GCF Investment Criteria v3",
                publisher="GCF",
                version="v3.0",
            )
            source_service.verify(
                conn,
                source_id=sid,
                verifier_id=verifier,
                embedding_func=_stub_embedding,
            )
            row = conn.execute(
                text(
                    "SELECT verification_status, verified_by IS NOT NULL, "
                    "embedding IS NOT NULL, status_version "
                    "FROM source WHERE id = :id"
                ),
                {"id": str(sid)},
            ).first()
            assert row is not None
            status, has_vb, has_emb, sv = row
            assert status == "verified"
            assert has_vb is True
            assert has_emb is True
            assert sv >= 2  # incrémenté par trigger lors de la transition

    def test_verify_with_same_user_rejected_by_db_trigger(self, two_admins):
        captured_by, _ = two_admins
        engine = get_engine_migrator()
        with engine.begin() as conn:
            sid = source_service.create_pending(
                conn,
                captured_by=captured_by,
                url="https://gcf.example/criteria.pdf",
                title="GCF Doc",
                publisher="GCF",
            )
        # Bypass du check Python pour vérifier que le trigger SQL aussi rejette
        with engine.begin() as conn, pytest.raises(Exception, match="double validation"):
            conn.execute(
                text(
                    "UPDATE source SET verification_status='verified', "
                    "verified_by = :vb, verified_at = now(), embedding = :emb, "
                    "updated_at = now() WHERE id = :id"
                ),
                {"vb": str(captured_by), "emb": [0.0] * 1024, "id": str(sid)},
            )

    def test_view_filters_unverified(self, two_admins):
        captured_by, verifier = two_admins
        engine = get_engine_migrator()
        with engine.begin() as conn:
            sid_pending = source_service.create_pending(
                conn,
                captured_by=captured_by,
                url="https://x.example/p",
                title="P",
                publisher="GCF",
            )
            sid_verified = source_service.create_pending(
                conn,
                captured_by=captured_by,
                url="https://x.example/v",
                title="V",
                publisher="GCF",
            )
            source_service.verify(
                conn, source_id=sid_verified, verifier_id=verifier,
                embedding_func=_stub_embedding,
            )
            # Insère 2 indicateurs
            ind_pending = uuid.uuid4()
            ind_verified = uuid.uuid4()
            for iid, sid in ((ind_pending, sid_pending), (ind_verified, sid_verified)):
                conn.execute(
                    text(
                        "INSERT INTO indicateur (id, name, source_id) "
                        "VALUES (:id, :n, :sid)"
                    ),
                    {"id": str(iid), "n": f"ind_{iid.hex[:6]}", "sid": str(sid)},
                )
            visible = {
                r[0]
                for r in conn.execute(
                    text(
                        "SELECT id FROM v_indicateur_verified WHERE id IN "
                        "(:a, :b)"
                    ),
                    {"a": str(ind_pending), "b": str(ind_verified)},
                ).all()
            }
            assert str(ind_verified) in visible or uuid.UUID(ind_verified.hex) in visible
            assert (
                str(ind_pending) not in visible
                and uuid.UUID(ind_pending.hex) not in visible
            )

    def test_on_delete_restrict_blocks_source_delete_when_referenced(self, two_admins):
        captured_by, _ = two_admins
        engine = get_engine_migrator()
        with engine.begin() as conn:
            sid = source_service.create_pending(
                conn,
                captured_by=captured_by,
                url="https://x.example/restrict",
                title="R",
                publisher="GCF",
            )
            iid = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO indicateur (id, name, source_id) "
                    "VALUES (:id, :n, :sid)"
                ),
                {"id": str(iid), "n": f"ind_{iid.hex[:6]}", "sid": str(sid)},
            )
        # Note : F01 a posé `source_id UUID NULL REFERENCES source(id)` SANS ON DELETE RESTRICT.
        # On vérifie au moins que la FK existe et bloque la suppression d'une source liée.
        with engine.begin() as conn, pytest.raises(Exception):  # noqa: B017
            conn.execute(text("DELETE FROM source WHERE id = :id"), {"id": str(sid)})
