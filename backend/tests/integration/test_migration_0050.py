"""F50 (T015) — vérifie l'état post-migration 0026/0027.

La migration ``0026_f50_documents_ui_extensions`` ajoute des colonnes à
``document_entreprise`` et crée la table ``document_link_projet`` (M:N) avec
RLS ``tenant_isolation``. ``0027_f50_document_tags`` ajoute la colonne
``tags TEXT[]`` + index GIN.

Ces tests vérifient l'état attendu en post-upgrade (le head courant de la
suite) plutôt que d'exécuter une rollback intrusive : la migration est
gardée par ``test_migration_idempotency.py`` qui couvre déjà
``upgrade → downgrade → upgrade``. Ici on s'assure que les colonnes,
la table, les index et la policy RLS sont bien en place pour les tests
fonctionnels F50 qui en dépendent.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.conftest import requires_db


@requires_db
@pytest.mark.integration
def test_document_entreprise_has_f50_columns(db_engine):
    """Colonnes ajoutées sur ``document_entreprise`` (T001 / 0026 + 0027)."""
    expected = {
        "content_sha256",
        "extraction_payload",
        "extraction_validated_at",
        "extraction_validated_by",
        "extraction_validation_payload",
        "purge_scheduled_at",
        "tags",
    }
    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'document_entreprise'"
            )
        ).all()
    cols = {r[0] for r in rows}
    missing = expected - cols
    assert not missing, f"Colonnes F50 manquantes : {missing}"


@requires_db
@pytest.mark.integration
def test_document_entreprise_column_types(db_engine):
    """Types attendus sur les colonnes F50 (BYTEA pour SHA256, JSONB pour payload)."""
    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT column_name, data_type, udt_name "
                "FROM information_schema.columns "
                "WHERE table_name = 'document_entreprise' "
                "AND column_name IN ('content_sha256', 'extraction_payload', "
                "'extraction_validated_at', 'extraction_validation_payload', "
                "'purge_scheduled_at', 'tags')"
            )
        ).all()
    types = {r[0]: (r[1], r[2]) for r in rows}
    assert types["content_sha256"][1] == "bytea"
    assert types["extraction_payload"][0] == "jsonb"
    assert types["extraction_validation_payload"][0] == "jsonb"
    assert types["extraction_validated_at"][0] == "timestamp with time zone"
    assert types["purge_scheduled_at"][0] == "timestamp with time zone"
    # tags est TEXT[] → data_type = ARRAY, udt_name = _text.
    assert types["tags"][0] == "ARRAY"
    assert types["tags"][1] == "_text"


@requires_db
@pytest.mark.integration
def test_document_link_projet_table_exists(db_engine):
    """Table ``document_link_projet`` créée par 0026."""
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'document_link_projet'"
            )
        ).first()
    assert row is not None, "table document_link_projet absente"


@requires_db
@pytest.mark.integration
def test_document_link_projet_columns(db_engine):
    """Colonnes attendues + UNIQUE (document_id, projet_id)."""
    with db_engine.connect() as c:
        cols = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'document_link_projet'"
                )
            ).all()
        }
    expected = {
        "id",
        "account_id",
        "document_id",
        "projet_id",
        "created_at",
        "created_by",
    }
    assert expected <= cols, f"Colonnes manquantes : {expected - cols}"

    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'document_link_projet'"
            )
        ).all()
    defs = "\n".join(r[0] for r in rows)
    # UNIQUE (document_id, projet_id) — créé par CREATE TABLE.
    assert "UNIQUE" in defs.upper()
    assert "document_id" in defs and "projet_id" in defs


@requires_db
@pytest.mark.integration
def test_document_entreprise_indexes_present(db_engine):
    """Index F50 (sha unique partiel, purge_scheduled, tags GIN) présents."""
    with db_engine.connect() as c:
        names = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'document_entreprise'"
                )
            ).all()
        }
    assert "uq_document_entreprise_account_sha" in names
    assert "idx_document_entreprise_purge_scheduled" in names
    assert "idx_document_entreprise_tags" in names


@requires_db
@pytest.mark.integration
def test_document_link_projet_indexes_present(db_engine):
    """Index secondaires F50 sur la table de liens."""
    with db_engine.connect() as c:
        names = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'document_link_projet'"
                )
            ).all()
        }
    assert "idx_document_link_projet_projet" in names
    assert "idx_document_link_projet_document" in names


@requires_db
@pytest.mark.integration
def test_document_link_projet_rls_enabled(db_engine):
    """RLS doit être activée et FORCEd sur document_link_projet."""
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relname = 'document_link_projet'"
            )
        ).first()
    assert row is not None
    rls_enabled, rls_forced = row
    assert rls_enabled is True, "RLS non activée sur document_link_projet"
    assert rls_forced is True, "RLS non FORCEd sur document_link_projet"


@requires_db
@pytest.mark.integration
def test_document_link_projet_tenant_policy(db_engine):
    """Policy RLS ``tenant_isolation`` doit exister et référencer current_setting."""
    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT polname, pg_get_expr(polqual, polrelid) AS using_expr, "
                "pg_get_expr(polwithcheck, polrelid) AS check_expr "
                "FROM pg_policy "
                "WHERE polrelid = 'document_link_projet'::regclass"
            )
        ).all()
    by_name = {r[0]: (r[1], r[2]) for r in rows}
    assert "tenant_isolation" in by_name, f"Policies présentes : {list(by_name)}"
    using_expr, check_expr = by_name["tenant_isolation"]
    assert "current_setting" in (using_expr or "")
    assert "app.current_account_id" in (using_expr or "")
    assert "current_setting" in (check_expr or "")


@requires_db
@pytest.mark.integration
def test_document_link_projet_grants(db_engine):
    """Grants minimaux SELECT/INSERT/DELETE pour app_user."""
    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT privilege_type FROM information_schema.role_table_grants "
                "WHERE table_name = 'document_link_projet' AND grantee = 'app_user'"
            )
        ).all()
    privileges = {r[0] for r in rows}
    # 0026 GRANT SELECT, INSERT, UPDATE, DELETE ON document_link_projet TO app_user.
    assert {"SELECT", "INSERT", "DELETE"} <= privileges, (
        f"Grants manquants pour app_user : {privileges}"
    )
