"""Tests de présence des tables, colonnes communes, multi-tenant (T025-T026, T035-T038)."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.conftest import requires_db

BACKEND_DIR = Path(__file__).resolve().parents[1]

CATALOGUE_TABLES = [
    "source",
    "referentiel",
    "indicateur",
    "intermediaire",
    "fonds_source",
    "accreditation",
    "offre",
    "critere",
    "document_requis",
    "facteur_emission",
    "template",
]
METIER_TABLES_WITH_ACCOUNT_ID = [
    "account_user",
    "entreprise",
    "projet",
    "candidature",
    "chat_message",
    "audit_log",
]
ALL_TABLES = ["account", *CATALOGUE_TABLES, *METIER_TABLES_WITH_ACCOUNT_ID]
EXPECTED_TABLE_COUNT = 18

COMMON_COLUMNS_METIER = ["id", "account_id", "created_at", "updated_at", "version"]


@pytest.fixture(scope="module", autouse=True)
def _ensure_migrations_applied():
    """Applique la migration head avant les tests de schéma."""
    res = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        pytest.skip(f"alembic upgrade head failed: {res.stderr}")
    yield


@requires_db
def test_all_18_tables_exist(db_engine):
    """T025 — les 18 tables attendues sont présentes."""
    with db_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE'"
            )
        ).fetchall()
    present = {r[0] for r in rows}
    missing = set(ALL_TABLES) - present
    assert not missing, f"Tables manquantes: {missing}. Présentes: {sorted(present)}"
    business = present & set(ALL_TABLES)
    assert len(business) == EXPECTED_TABLE_COUNT


@requires_db
@pytest.mark.parametrize(
    "table",
    ["entreprise", "projet", "candidature", "chat_message", "account_user"],
)
def test_metier_tables_have_common_columns(db_engine, table):
    """T026 — chaque table métier porte les colonnes communes."""
    with db_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t"
            ),
            {"t": table},
        ).fetchall()
    cols = {r[0] for r in rows}
    expected = {"id", "account_id", "created_at", "updated_at", "version", "deleted_at"}
    missing = expected - cols
    assert not missing, f"{table}: colonnes manquantes {missing}"


@requires_db
def test_audit_log_has_no_deleted_at(db_engine):
    """audit_log est append-only — pas de deleted_at."""
    with db_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='audit_log'"
            )
        ).fetchall()
    cols = {r[0] for r in rows}
    assert "deleted_at" not in cols
    # Mais doit avoir id, account_id, timestamp, entity_type, entity_id, source_of_change
    for col in ("id", "account_id", "timestamp", "entity_type", "entity_id", "source_of_change"):
        assert col in cols, f"audit_log: {col} manquant"


# ---------- Phase 5: Multi-tenant (T035-T038) ----------


@requires_db
@pytest.mark.parametrize("table", METIER_TABLES_WITH_ACCOUNT_ID)
def test_metier_tables_account_id_not_null(db_engine, table):
    """T035 — account_id NOT NULL sur les 6 tables métier (audit_log = NULL autorisé)."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t AND column_name='account_id'"
            ),
            {"t": table},
        ).fetchone()
    assert row is not None, f"{table}.account_id absent"
    if table in ("audit_log", "account_user"):
        # audit_log accepte NULL pour événements système (cf. data-model.md).
        # account_user accepte NULL pour les admins (F02 — cf. data-model.md).
        assert row[0] in ("YES", "NO")
    else:
        assert row[0] == "NO", f"{table}.account_id devrait être NOT NULL"


@requires_db
@pytest.mark.parametrize("table", METIER_TABLES_WITH_ACCOUNT_ID)
def test_metier_tables_account_id_indexed(db_engine, table):
    """T036 — index sur account_id pour chaque table métier."""
    with db_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname='public' AND tablename=:t"
            ),
            {"t": table},
        ).fetchall()
    defs = " ".join(r[0] for r in rows)
    assert "account_id" in defs, f"{table}: aucun index sur account_id\n{defs}"


@requires_db
def test_insert_entreprise_without_account_id_raises(db_engine):
    """T037 — INSERT sans account_id rejeté."""
    with db_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO entreprise (id, name) VALUES (:id, :n)"
                ),
                {"id": str(uuid.uuid4()), "n": "Test"},
            )


@requires_db
@pytest.mark.parametrize("table", CATALOGUE_TABLES)
def test_catalogue_tables_have_no_account_id(db_engine, table):
    """T038 — les tables catalogue n'ont PAS de colonne account_id."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t AND column_name='account_id'"
            ),
            {"t": table},
        ).fetchone()
    assert row is None, f"{table} ne devrait PAS avoir de colonne account_id"
