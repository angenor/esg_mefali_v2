"""F25 — Tests unitaires de candidature_service avec FakeSession."""

from __future__ import annotations

import uuid

import pytest

from app.matching import candidature_service as csvc
from tests.unit.matching.test_service import (
    ACCOUNT_ID,
    OFFRE_ID,
    PROJET_ID,
    FakeResult,
    FakeSession,
    _fake_offre_row,
    _fake_projet,
)


def test_canonical_json_sorted_compact():
    s = csvc._canonical_json({"b": 1, "a": 2})
    assert s == '{"a":2,"b":1}'


def test_hash_stable_and_length():
    h1 = csvc._hash({"x": 1, "y": "a"})
    h2 = csvc._hash({"y": "a", "x": 1})
    assert h1 == h2
    assert len(h1) == 64


def test_create_candidature_projet_not_found():
    db = FakeSession()
    db.queue_results(FakeResult(None))
    with pytest.raises(csvc.ProjetNotFound):
        csvc.create_candidature(
            db, account_id=ACCOUNT_ID, projet_id=PROJET_ID, offre_id=OFFRE_ID
        )


def test_create_candidature_offre_not_found():
    db = FakeSession()
    db.queue_results(FakeResult(_fake_projet()))
    db.queue_results(FakeResult([]))
    with pytest.raises(csvc.OffreNotFound):
        csvc.create_candidature(
            db, account_id=ACCOUNT_ID, projet_id=PROJET_ID, offre_id=OFFRE_ID
        )


def test_create_candidature_happy_path():
    db = FakeSession()
    # _build_snapshot calls _load_projet + _load_offres + matching_service.detail (load+offres)
    db.queue_results(FakeResult(_fake_projet()))
    db.queue_results(FakeResult([_fake_offre_row()]))
    db.queue_results(FakeResult(_fake_projet()))
    db.queue_results(FakeResult([_fake_offre_row()]))
    db.queue_results(FakeResult(None))  # INSERT candidature
    db.queue_results(FakeResult(None))  # record_audit
    user_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    out = csvc.create_candidature(
        db,
        account_id=ACCOUNT_ID,
        projet_id=PROJET_ID,
        offre_id=OFFRE_ID,
        user_id=user_id,
    )
    assert out["statut"] == "brouillon"
    assert len(out["snapshot_hash"]) == 64
    inserts = [s for s, _ in db.executed if "INSERT INTO candidature" in s]
    assert len(inserts) == 1


def test_build_snapshot_contains_keys():
    db = FakeSession()
    db.queue_results(FakeResult(_fake_projet()))
    db.queue_results(FakeResult([_fake_offre_row()]))
    db.queue_results(FakeResult(_fake_projet()))
    db.queue_results(FakeResult([_fake_offre_row()]))
    snap = csvc._build_snapshot(
        db, account_id=ACCOUNT_ID, projet_id=PROJET_ID, offre_id=OFFRE_ID
    )
    assert snap["schema_version"] == 1
    assert "captured_at" in snap
    assert snap["projet"]["id"] == str(PROJET_ID)
    assert snap["offre"]["id"] == str(OFFRE_ID)
    assert "scoring" in snap
