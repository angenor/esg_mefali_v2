"""F04 — Pydantic snapshot v1 schema unit tests (T025, T080)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.snapshot.schema import (
    CandidatureSnapshotV1,
    Money,
    OffreRef,
    ReferentielRef,
    SnapshotScores,
)


def _sample_snapshot_dict() -> dict:
    return {
        "schema_version": "1",
        "referentiel": {
            "logical_id": str(uuid4()),
            "version": 2,
            "valid_from": datetime.now(tz=UTC).isoformat(),
        },
        "offre": {"id": str(uuid4()), "criteres": []},
        "projet_state": {"nom": "X"},
        "scores": {
            "global": {"amount": "100.00", "currency": "XOF"},
            "per_critere": {},
        },
        "sources": [],
    }


def test_money_amount_format() -> None:
    Money(amount="0", currency="XOF")
    Money(amount="-12.34", currency="EUR")
    with pytest.raises(ValidationError):
        Money(amount="abc", currency="XOF")
    with pytest.raises(ValidationError):
        Money(amount="1", currency="usd")  # lower-case rejected


def test_snapshot_round_trip() -> None:
    raw = _sample_snapshot_dict()
    parsed = CandidatureSnapshotV1.model_validate(raw)
    again = parsed.model_dump(mode="json", by_alias=True)
    assert again["schema_version"] == "1"
    # Field is `global_` in Python but exported as `global` via alias.
    assert again["scores"]["global"]["amount"] == "100.00"


def test_snapshot_extra_forbid() -> None:
    raw = _sample_snapshot_dict()
    raw["unknown"] = "boom"
    with pytest.raises(ValidationError):
        CandidatureSnapshotV1.model_validate(raw)


def test_snapshot_schema_version_const() -> None:
    raw = _sample_snapshot_dict()
    raw["schema_version"] = "2"
    with pytest.raises(ValidationError):
        CandidatureSnapshotV1.model_validate(raw)


def test_matches_json_schema_required_keys() -> None:
    """The Pydantic model must cover every required key in contracts/snapshot.schema.json."""
    repo_root = Path(__file__).resolve().parents[4]
    schema_path = repo_root / "specs" / "004-audit-log-versioning" / "contracts" / "snapshot.schema.json"
    schema = json.loads(schema_path.read_text())
    required = set(schema["required"])
    parsed = CandidatureSnapshotV1.model_validate(_sample_snapshot_dict())
    dumped = parsed.model_dump(mode="json", by_alias=True)
    assert required.issubset(set(dumped.keys()))


def test_offre_with_critere_refs() -> None:
    o = OffreRef(
        id=uuid4(),
        criteres=[{"logical_id": str(uuid4()), "version": 3}],  # type: ignore[list-item]
    )
    assert o.criteres[0].version == 3


def test_scores_alias() -> None:
    s = SnapshotScores(
        **{"global": Money(amount="0", currency="XOF"), "per_critere": {}}
    )
    out = s.model_dump(by_alias=True)
    assert "global" in out and "global_" not in out


def test_referentiel_ref_version_min_1() -> None:
    with pytest.raises(ValidationError):
        ReferentielRef(
            logical_id=uuid4(),
            version=0,
            valid_from=datetime.now(tz=UTC),
        )
