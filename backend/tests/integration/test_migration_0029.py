"""F51 (T016) — vérifie l'état post-migration 0029.

La migration ``0029_f51_wizard_and_simulation_savee`` :
- ajoute ``step_courant``, ``progression_pct``, ``draft_snapshot_json`` à ``candidature``
- étend ``candidature_snapshot_guard`` pour figer ``draft_snapshot_json`` post-submit
- crée les index partiels ``idx_candidature_drafts`` et ``idx_candidature_submitted``
- crée la table ``simulation_savee`` avec RLS ``tenant_isolation``
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.conftest import requires_db


@requires_db
@pytest.mark.integration
def test_candidature_has_f51_columns(db_engine):
    """Colonnes ajoutées sur ``candidature``."""
    expected = {"step_courant", "progression_pct", "draft_snapshot_json"}
    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'candidature'"
            )
        ).all()
    cols = {r[0] for r in rows}
    missing = expected - cols
    assert not missing, f"Colonnes F51 manquantes sur candidature : {missing}"


@requires_db
@pytest.mark.integration
def test_candidature_check_constraints(db_engine):
    """CHECK constraints step_courant ∈ [1..5], progression_pct ∈ [0..100]."""
    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'candidature'::regclass "
                "AND contype = 'c' "
                "AND conname IN ('chk_candidature_step_courant', 'chk_candidature_progression_pct')"
            )
        ).all()
    names = {r[0] for r in rows}
    assert "chk_candidature_step_courant" in names
    assert "chk_candidature_progression_pct" in names


@requires_db
@pytest.mark.integration
def test_candidature_snapshot_guard_function_exists(db_engine):
    """La fonction ``candidature_snapshot_guard`` est présente (étendue par F51)."""
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT pg_get_functiondef(oid) FROM pg_proc "
                "WHERE proname = 'candidature_snapshot_guard'"
            )
        ).first()
    assert row is not None, "Fonction candidature_snapshot_guard absente"
    body = row[0]
    # F51 a étendu le guard pour également figer draft_snapshot_json post-submit.
    assert "draft_snapshot_json" in body, (
        "Le guard F51 doit mentionner draft_snapshot_json (extension de la "
        "fonction post-submit immutability)"
    )


@requires_db
@pytest.mark.integration
def test_candidature_partial_indexes(db_engine):
    """Index partiels ``idx_candidature_drafts`` et ``idx_candidature_submitted``."""
    with db_engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'candidature' "
                "AND indexname IN ('idx_candidature_drafts', 'idx_candidature_submitted')"
            )
        ).all()
    names = {r[0] for r in rows}
    assert "idx_candidature_drafts" in names
    assert "idx_candidature_submitted" in names


@requires_db
@pytest.mark.integration
def test_simulation_savee_table_exists(db_engine):
    """Table ``simulation_savee`` créée."""
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE tablename = 'simulation_savee'"
            )
        ).first()
    assert row is not None, "Table simulation_savee absente"


@requires_db
@pytest.mark.integration
def test_simulation_savee_rls_policy(db_engine):
    """Politique RLS ``tenant_isolation`` sur ``simulation_savee``."""
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT policyname FROM pg_policies "
                "WHERE tablename = 'simulation_savee' AND policyname = 'tenant_isolation'"
            )
        ).first()
    assert row is not None, "Policy tenant_isolation absente sur simulation_savee"


@requires_db
@pytest.mark.integration
def test_simulation_savee_rls_enabled(db_engine):
    """RLS activée (relrowsecurity = true) sur ``simulation_savee``."""
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = 'simulation_savee'"
            )
        ).first()
    assert row is not None and row[0] is True, (
        "RLS doit être activée sur simulation_savee (P2)"
    )


@requires_db
@pytest.mark.integration
def test_simulation_savee_partial_index(db_engine):
    """Index partiel ``idx_simulation_savee_account_recent``."""
    with db_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'simulation_savee' "
                "AND indexname = 'idx_simulation_savee_account_recent'"
            )
        ).first()
    assert row is not None
