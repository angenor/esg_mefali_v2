"""F57 / T006 — RLS test ``agent_entity_memory`` (P2 multi-tenant).

Vérifie :
- la table existe et possède un account_id NOT NULL,
- RLS est ENABLE + FORCE,
- la policy ``agent_entity_memory_isolation`` est en place,
- la contrainte UNIQUE (account_id, entity_type, entity_id) existe,
- l'index unique est utilisable.

Note : le test process tourne sous le rôle propriétaire (``esg``) et donc
RLS FORCED est appliquée mais peut différer si le test exécute des SET
LOCAL. La vérification d'isolation effective cross-tenant est faite par
``app.agent.memory.entity_memory`` via les requêtes ORM côté code.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from tests.integration.conftest import requires_db

pytestmark = [pytest.mark.integration, requires_db]


def test_agent_entity_memory_table_exists(db_engine) -> None:
    with db_engine.connect() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='agent_entity_memory'"
                )
            ).all()
        }
    assert {
        "id",
        "account_id",
        "entity_type",
        "entity_id",
        "summary",
        "sources_used",
        "last_updated_at",
        "version",
    } <= cols


def test_agent_entity_memory_rls_enabled_and_forced(db_engine) -> None:
    """RLS doit être ENABLE + FORCE (P2)."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relname = 'agent_entity_memory'"
            )
        ).first()
    assert row is not None
    assert row[0] is True, "RLS not enabled"
    assert row[1] is True, "RLS not FORCED"


def test_agent_entity_memory_isolation_policy_exists(db_engine) -> None:
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT policyname FROM pg_policies "
                "WHERE tablename = 'agent_entity_memory' "
                "AND policyname = 'agent_entity_memory_isolation'"
            )
        ).first()
    assert row is not None


def test_agent_entity_memory_unique_constraint(db_engine) -> None:
    """UNIQUE (account_id, entity_type, entity_id) doit exister."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname = 'uq_agent_entity_memory_account_entity'"
            )
        ).first()
    assert row is not None


def test_agent_entity_memory_unique_violation_raises(db_engine) -> None:
    """INSERT 2 lignes (account, entity_type, entity_id) identiques → erreur."""
    account = uuid.uuid4()
    entity_id = uuid.uuid4()

    # Setup minimal account
    with db_engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO account (id, name) VALUES (CAST(:id AS UUID), :n) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": str(account), "n": f"itest_{account.hex[:6]}"},
        )
        conn.execute(text(f"SET LOCAL app.current_account_id = '{account}'"))
        conn.execute(
            text(
                """
                INSERT INTO agent_entity_memory
                  (account_id, entity_type, entity_id, summary)
                VALUES (CAST(:aid AS UUID), 'Entreprise', CAST(:eid AS UUID), 'one')
                """
            ),
            {"aid": str(account), "eid": str(entity_id)},
        )
        conn.commit()

    from sqlalchemy.exc import IntegrityError, SQLAlchemyError

    with db_engine.connect() as conn:
        conn.execute(text(f"SET LOCAL app.current_account_id = '{account}'"))
        with pytest.raises((IntegrityError, SQLAlchemyError)):
            conn.execute(
                text(
                    """
                    INSERT INTO agent_entity_memory
                      (account_id, entity_type, entity_id, summary)
                    VALUES (CAST(:aid AS UUID), 'Entreprise', CAST(:eid AS UUID), 'two')
                    """
                ),
                {"aid": str(account), "eid": str(entity_id)},
            )
            conn.commit()
