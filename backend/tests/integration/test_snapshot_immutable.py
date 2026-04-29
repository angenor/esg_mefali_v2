"""F04 — Snapshot immutability trigger (T083, SC-008)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import InternalError, ProgrammingError

from tests.conftest import DB_AVAILABLE

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_snapshot_immutable_trigger_blocks_update(db_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        # Bootstrap minimal candidature row (account, projet, offre).
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'A', now(), now()) RETURNING id"
            )
        ).scalar_one()
        ent_id = db.execute(
            text(
                "INSERT INTO entreprise (id, account_id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, 'E', now(), now()) RETURNING id"
            ),
            {"a": acc_id},
        ).scalar_one()
        proj_id = db.execute(
            text(
                "INSERT INTO projet (id, account_id, entreprise_id, nom, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'P', now(), now()) RETURNING id"
            ),
            {"a": acc_id, "e": ent_id},
        ).scalar_one()
        fonds_id = db.execute(
            text(
                "INSERT INTO fonds_source (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'F', now(), now()) RETURNING id"
            )
        ).scalar_one()
        offre_id = db.execute(
            text(
                "INSERT INTO offre (id, fonds_id, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :f, now(), now()) RETURNING id"
            ),
            {"f": fonds_id},
        ).scalar_one()

        cand_id = db.execute(
            text(
                "INSERT INTO candidature "
                "(id, account_id, projet_id, offre_id, snapshot_json, submitted_at, "
                " created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :p, :o, "
                "        CAST('{\"k\":\"v\"}' AS JSONB), :ts, now(), now()) "
                "RETURNING id"
            ),
            {"a": acc_id, "p": proj_id, "o": offre_id,
             "ts": datetime.now(tz=UTC)},
        ).scalar_one()

        # Attempt to mutate snapshot_json after submission -> trigger raises.
        with pytest.raises((InternalError, ProgrammingError, Exception)) as exc:
            db.execute(
                text(
                    "UPDATE candidature SET snapshot_json = "
                    "CAST('{\"k\":\"hacked\"}' AS JSONB) WHERE id = :cid"
                ),
                {"cid": cand_id},
            )
            db.flush()
        assert "immutable" in str(exc.value).lower()
        db.rollback()


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
def test_snapshot_mutable_before_submission(db_engine) -> None:
    """The trigger only fires once submitted_at is set."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'A', now(), now()) RETURNING id"
            )
        ).scalar_one()
        ent_id = db.execute(
            text(
                "INSERT INTO entreprise (id, account_id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, 'E', now(), now()) RETURNING id"
            ),
            {"a": acc_id},
        ).scalar_one()
        proj_id = db.execute(
            text(
                "INSERT INTO projet (id, account_id, entreprise_id, nom, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'P', now(), now()) RETURNING id"
            ),
            {"a": acc_id, "e": ent_id},
        ).scalar_one()
        fonds_id = db.execute(
            text(
                "INSERT INTO fonds_source (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'F', now(), now()) RETURNING id"
            )
        ).scalar_one()
        offre_id = db.execute(
            text(
                "INSERT INTO offre (id, fonds_id, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :f, now(), now()) RETURNING id"
            ),
            {"f": fonds_id},
        ).scalar_one()
        cand_id = db.execute(
            text(
                "INSERT INTO candidature "
                "(id, account_id, projet_id, offre_id, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :p, :o, now(), now()) RETURNING id"
            ),
            {"a": acc_id, "p": proj_id, "o": offre_id},
        ).scalar_one()
        # Draft mutation is allowed.
        db.execute(
            text(
                "UPDATE candidature SET snapshot_json = CAST(:snap AS JSONB) "
                "WHERE id = :cid"
            ),
            {"cid": cand_id, "snap": '{"draft": true}'},
        )
        db.rollback()
