"""F04 — EXCLUDE constraint enforcement (T063, SC-004).

For each of the seven versioned tables, attempting to INSERT an overlapping
window for the same logical_id must be rejected by Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from tests.conftest import DB_AVAILABLE

pytestmark = pytest.mark.integration

# Tables that physically exist today (others are deferred to F09).
EXISTING_VERSIONED = ("indicateur", "facteur_emission", "template", "critere")


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.parametrize("table", EXISTING_VERSIONED)
def test_overlap_rejected_per_table(db_engine, table: str) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        logical = uuid4()
        now = datetime.now(tz=UTC)
        later = now + timedelta(days=10)

        # Insert minimal viable rows per table-specific NOT NULL columns.
        common = {
            "lid": str(logical),
            "from1": now,
            "to1": None,
            "from2": now + timedelta(days=1),
            "to2": later,
        }
        if table == "indicateur":
            insert_a = (
                "INSERT INTO indicateur (id, name, logical_id, valid_from, valid_to) "
                "VALUES (gen_random_uuid(), 'I', CAST(:lid AS UUID), :from1, :to1)"
            )
            insert_b = (
                "INSERT INTO indicateur (id, name, logical_id, valid_from, valid_to) "
                "VALUES (gen_random_uuid(), 'I2', CAST(:lid AS UUID), :from2, :to2)"
            )
        elif table == "facteur_emission":
            insert_a = (
                "INSERT INTO facteur_emission "
                "(id, name, valeur, unite, logical_id, valid_from, valid_to) "
                "VALUES (gen_random_uuid(), 'F', 1, 'kgCO2', CAST(:lid AS UUID), :from1, :to1)"
            )
            insert_b = (
                "INSERT INTO facteur_emission "
                "(id, name, valeur, unite, logical_id, valid_from, valid_to) "
                "VALUES (gen_random_uuid(), 'F', 2, 'kgCO2', CAST(:lid AS UUID), :from2, :to2)"
            )
        elif table == "template":
            # template requires offre_id NOT NULL — fetch or create one.
            offre = db.execute(
                text("SELECT id FROM offre LIMIT 1")
            ).mappings().first()
            if offre is None:
                # Need a fonds first.
                fonds_id = db.execute(
                    text(
                        "INSERT INTO fonds_source (id, name) "
                        "VALUES (gen_random_uuid(), 'F') RETURNING id"
                    )
                ).scalar_one()
                offre_id = db.execute(
                    text(
                        "INSERT INTO offre (id, fonds_id) "
                        "VALUES (gen_random_uuid(), :fid) RETURNING id"
                    ),
                    {"fid": fonds_id},
                ).scalar_one()
            else:
                offre_id = offre["id"]
            common["oid"] = offre_id
            insert_a = (
                "INSERT INTO template (id, offre_id, name, logical_id, valid_from, valid_to) "
                "VALUES (gen_random_uuid(), :oid, 'T', CAST(:lid AS UUID), :from1, :to1)"
            )
            insert_b = (
                "INSERT INTO template (id, offre_id, name, logical_id, valid_from, valid_to) "
                "VALUES (gen_random_uuid(), :oid, 'T2', CAST(:lid AS UUID), :from2, :to2)"
            )
        elif table == "critere":
            # critere requires either offre_id or referentiel_id (XOR).
            ref_id = db.execute(
                text(
                    "INSERT INTO referentiel (id, name, version) "
                    "VALUES (gen_random_uuid(), 'R', 'v1') RETURNING id"
                )
            ).scalar_one()
            common["rid_ref"] = ref_id
            insert_a = (
                "INSERT INTO critere (id, referentiel_id, logical_id, valid_from, valid_to) "
                "VALUES (gen_random_uuid(), :rid_ref, CAST(:lid AS UUID), :from1, :to1)"
            )
            insert_b = (
                "INSERT INTO critere (id, referentiel_id, logical_id, valid_from, valid_to) "
                "VALUES (gen_random_uuid(), :rid_ref, CAST(:lid AS UUID), :from2, :to2)"
            )
        else:
            pytest.skip(f"no fixture for table {table}")

        db.execute(text(insert_a), common)

        with pytest.raises((IntegrityError, ProgrammingError, Exception)) as excinfo:
            db.execute(text(insert_b), common)
            db.flush()
        msg = str(excinfo.value).lower()
        assert "exclu" in msg or "conflict" in msg or "overlap" in msg or "violates" in msg
        db.rollback()
