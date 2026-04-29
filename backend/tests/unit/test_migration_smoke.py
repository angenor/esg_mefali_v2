"""F03 — Smoke test migration 0003.

Vérifie que :
- L'enum ``source_verification_status`` existe avec 4 valeurs.
- Les colonnes renforcées de ``source`` existent.
- Les indexes sont posés.
- Les vues v_<entity>_verified existent.
- La table ``unsourced_claim_log`` existe avec RLS activée.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.conftest import requires_db


@requires_db
@pytest.mark.unit
def test_source_enum_exists(db_engine):
    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT enumlabel FROM pg_enum e "
                "JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname='source_verification_status' ORDER BY enumlabel"
            )
        ).all()
    labels = {r[0] for r in rows}
    assert labels == {"pending", "verified", "outdated", "rejected"}


@requires_db
@pytest.mark.unit
def test_source_columns_exist(db_engine):
    with db_engine.connect() as c:
        cols = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='source'"
                )
            ).all()
        }
    for required in (
        "embedding",
        "tsv",
        "verified_at",
        "notes",
        "status_version",
        "verification_status",
    ):
        assert required in cols, f"missing column: {required}"


@requires_db
@pytest.mark.unit
def test_source_indexes_exist(db_engine):
    with db_engine.connect() as c:
        idx = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename='source'"
                )
            ).all()
        }
    for needed in (
        "source_tsv_gin",
        "source_embedding_ivf",
        "source_status_idx",
        "source_publisher_idx",
    ):
        assert needed in idx, f"missing index: {needed}"


@requires_db
@pytest.mark.unit
def test_views_exist(db_engine):
    with db_engine.connect() as c:
        views = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT table_name FROM information_schema.views "
                    "WHERE table_name LIKE 'v_%_verified'"
                )
            ).all()
        }
    for v in (
        "v_indicateur_verified",
        "v_critere_verified",
        "v_document_requis_verified",
        "v_facteur_emission_verified",
    ):
        assert v in views


@requires_db
@pytest.mark.unit
def test_unsourced_claim_log_exists_and_rls_enabled(db_engine):
    with db_engine.connect() as c:
        cols = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='unsourced_claim_log'"
                )
            ).all()
        }
        assert {"id", "account_id", "claim_text", "claim_text_normalized"} <= cols

        rls = c.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity "
                "FROM pg_class WHERE relname='unsourced_claim_log'"
            )
        ).first()
        assert rls is not None and rls[0] is True and rls[1] is True


@requires_db
@pytest.mark.unit
def test_source_triggers_exist(db_engine):
    with db_engine.connect() as c:
        trigs = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid = 'source'::regclass AND NOT tgisinternal"
                )
            ).all()
        }
    assert "source_double_validation" in trigs
    assert "source_status_version" in trigs
