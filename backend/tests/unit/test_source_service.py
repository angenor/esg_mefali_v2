"""F03 US1 — Tests unitaires du source_service.

Couvre :
- Refus transitions interdites (pending->outdated, rejected->* etc.).
- Refus double validation (verifier == captured_by) côté Python.
- Refus création URL non https.
- Embedding requis : si embedding_func raise, verify() raise SourceServiceError.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.services import source_service


def _engine_mock_for_status(status: str, captured_by: uuid.UUID, has_emb: bool = False):
    db = MagicMock()
    # _load_status retourne ces 3 valeurs
    row = MagicMock()
    row.__getitem__.side_effect = lambda i: {
        0: status, 1: str(captured_by), 2: has_emb
    }[i]
    db.execute.return_value.first.return_value = row
    return db


@pytest.mark.unit
def test_create_pending_requires_https():
    db = MagicMock()
    with pytest.raises(source_service.SourceServiceError):
        source_service.create_pending(
            db,
            captured_by=uuid.uuid4(),
            url="ftp://bad",
            title="x",
            publisher="GCF",
        )


@pytest.mark.unit
def test_verify_refuses_same_user_double_validation():
    captured_by = uuid.uuid4()
    sid = uuid.uuid4()
    db = _engine_mock_for_status("pending", captured_by)
    with pytest.raises(source_service.SourceServiceError, match="double validation"):
        source_service.verify(db, source_id=sid, verifier_id=captured_by)


@pytest.mark.unit
def test_verify_refuses_invalid_transition():
    captured_by = uuid.uuid4()
    sid = uuid.uuid4()
    db = _engine_mock_for_status("rejected", captured_by)
    with pytest.raises(source_service.SourceServiceError, match="transition not allowed"):
        source_service.verify(db, source_id=sid, verifier_id=uuid.uuid4())


@pytest.mark.unit
def test_verify_propagates_embedding_failure():
    captured_by = uuid.uuid4()
    verifier = uuid.uuid4()
    sid = uuid.uuid4()
    db = MagicMock()
    # _load_status branch
    status_row = MagicMock()
    status_row.__getitem__.side_effect = lambda i: {
        0: "pending", 1: str(captured_by), 2: False
    }[i]
    # Subsequent call returns mapping for embedding text
    mapping_row = {"title": "t", "publisher": "p", "notes": None}

    call_count = {"i": 0}

    def execute_side_effect(*args, **kwargs):
        call_count["i"] += 1
        m = MagicMock()
        if call_count["i"] == 1:
            m.first.return_value = status_row
        else:
            m.mappings.return_value.first.return_value = mapping_row
        return m

    db.execute.side_effect = execute_side_effect

    def boom(_texts):
        raise RuntimeError("VOYAGE_API_KEY missing")

    with pytest.raises(source_service.SourceServiceError, match="embedding failure"):
        source_service.verify(
            db,
            source_id=sid,
            verifier_id=verifier,
            embedding_func=boom,
        )


@pytest.mark.unit
def test_mark_outdated_only_from_verified():
    captured_by = uuid.uuid4()
    sid = uuid.uuid4()
    db = _engine_mock_for_status("pending", captured_by)
    with pytest.raises(source_service.SourceServiceError, match="transition not allowed"):
        source_service.mark_outdated(db, source_id=sid)


@pytest.mark.unit
def test_reject_only_from_pending():
    captured_by = uuid.uuid4()
    sid = uuid.uuid4()
    db = _engine_mock_for_status("verified", captured_by)
    with pytest.raises(source_service.SourceServiceError, match="transition not allowed"):
        source_service.reject(db, source_id=sid, reason="bad")


@pytest.mark.unit
def test_load_status_not_found():
    db = MagicMock()
    db.execute.return_value.first.return_value = None
    with pytest.raises(source_service.SourceServiceError, match="not found"):
        source_service._load_status(db, uuid.uuid4())
