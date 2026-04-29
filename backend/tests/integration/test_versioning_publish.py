"""F04 — publish_new_version + get_active integration (T060, T061, T062, T064)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.versioning.exceptions import OptimisticLockError
from app.versioning.helpers import get_active, publish_new_version
from tests.conftest import DB_AVAILABLE

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_publish_atomic_close_and_open(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        # Seed first row directly.
        code = f"PUB_A_{uuid4().hex[:6].upper()}"
        result = db.execute(
            text(
                "INSERT INTO indicateur (id, code, name, pillar, valid_from) "
                "VALUES (gen_random_uuid(), :code, 'Indic1', 'E', now()) "
                "RETURNING id, logical_id"
            ),
            {"code": code},
        ).mappings().first()
        logical_id = result["logical_id"]

        # Close the v1 row by status to avoid partial unique conflict on code.
        db.execute(
            text(
                "UPDATE indicateur SET status='outdated' WHERE id = :id"
            ),
            {"id": result["id"]},
        )
        code2 = code + "_V2"
        new_row = publish_new_version(
            db,
            table="indicateur",
            logical_id=logical_id,
            new_payload={"name": "Indic2", "code": code2, "pillar": "E"},
            version_at_load=1,
        )
        assert new_row["version"] == 2
        assert new_row["parent_id"] == result["id"]
        # Old row should now have valid_to set.
        old = db.execute(
            text("SELECT valid_to FROM indicateur WHERE id = :id"),
            {"id": result["id"]},
        ).mappings().first()
        assert old["valid_to"] is not None
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_publish_optimistic_lock(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        code = f"PUB_B_{uuid4().hex[:6].upper()}"
        seed = db.execute(
            text(
                "INSERT INTO indicateur (id, code, name, pillar) "
                "VALUES (gen_random_uuid(), :code, 'X', 'E') RETURNING logical_id"
            ),
            {"code": code},
        ).mappings().first()
        with pytest.raises(OptimisticLockError):
            publish_new_version(
                db,
                table="indicateur",
                logical_id=seed["logical_id"],
                new_payload={"name": "Y"},
                version_at_load=99,
            )
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_get_active_returns_correct_window(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        code = f"PUB_C_{uuid4().hex[:6].upper()}"
        seed = db.execute(
            text(
                "INSERT INTO indicateur (id, code, name, pillar) "
                "VALUES (gen_random_uuid(), :code, 'A', 'E') RETURNING logical_id"
            ),
            {"code": code},
        ).mappings().first()
        active = get_active(db, table="indicateur", logical_id=seed["logical_id"])
        assert active is not None
        assert active["name"] == "A"

        # Far in the future, the same logical_id is still active (valid_to NULL).
        future = datetime.now(tz=UTC) + timedelta(days=365)
        active2 = get_active(
            db, table="indicateur", logical_id=seed["logical_id"], at_timestamp=future
        )
        assert active2 is not None
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_get_active_none_when_unknown(db_engine) -> None:
    from uuid import uuid4

    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        active = get_active(db, table="indicateur", logical_id=uuid4())
        assert active is None


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_chain_of_publishes_no_overlap(db_engine) -> None:
    """T064 (light) — 5 successive publishes, then SQL audit for overlap = 0."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        code = f"PUB_D_{uuid4().hex[:6].upper()}"
        seed = db.execute(
            text(
                "INSERT INTO indicateur (id, code, name, pillar) "
                "VALUES (gen_random_uuid(), :code, 'C0', 'E') RETURNING logical_id"
            ),
            {"code": code},
        ).mappings().first()
        logical_id = seed["logical_id"]

        v = 1
        # Mark v1 as outdated to bypass partial unique on code.
        db.execute(
            text("UPDATE indicateur SET status='outdated' WHERE logical_id = CAST(:lid AS UUID)"),
            {"lid": str(logical_id)},
        )
        for i in range(5):
            new_code = f"{code}_V{i + 2}"
            row = publish_new_version(
                db,
                table="indicateur",
                logical_id=logical_id,
                new_payload={
                    "name": f"C{i + 1}",
                    "code": new_code,
                    "pillar": "E",
                    "status": "outdated",  # avoid partial unique conflict
                },
                version_at_load=v,
            )
            v = row["version"]

        overlap_count = db.execute(
            text(
                "SELECT count(*) FROM indicateur a "
                "JOIN indicateur b ON a.logical_id = b.logical_id "
                "  AND a.id <> b.id "
                "  AND tstzrange(a.valid_from, a.valid_to) "
                "      && tstzrange(b.valid_from, b.valid_to) "
                "WHERE a.logical_id = :lid"
            ),
            {"lid": str(logical_id)},
        ).scalar_one()
        assert overlap_count == 0
        db.rollback()
