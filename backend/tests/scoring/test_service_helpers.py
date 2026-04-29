"""F23 — Tests unitaires des helpers du service (sans DB)."""

from __future__ import annotations

import json
import uuid

from app.scoring.engine import (
    CoveredIndicator,
    MissingIndicator,
    ScoreResult,
)
from app.scoring.service import (
    _json_dumps,
    _retag_unmapped,
    _serialize_details,
)


def _make_result(*, missing_codes: list[str]) -> ScoreResult:
    return ScoreResult(
        score_global=80.0,
        scores_by_pillar={"E": 80.0},
        coverage_ratio=0.5,
        indicateurs_couverts=[
            CoveredIndicator(
                indicateur_id=uuid.uuid4(),
                indicateur_code="A",
                pillar="E",
                value=42,
                normalized_value=80.0,
                weight=1.0,
                contribution=80.0,
                source_id=uuid.uuid4(),
            )
        ],
        indicateurs_manquants=[
            MissingIndicator(
                indicateur_id=uuid.uuid4(),
                indicateur_code=code,
                pillar="S",
                reason="value_absent",
            )
            for code in missing_codes
        ],
        sources_used=[uuid.uuid4()],
    )


class TestRetagUnmapped:
    def test_no_unmapped_returns_same_reason(self) -> None:
        r = _make_result(missing_codes=["X"])
        out = _retag_unmapped(r, {})
        assert out.indicateurs_manquants[0].reason == "value_absent"

    def test_with_unmapped_overrides_reason(self) -> None:
        r = _make_result(missing_codes=["X"])
        out = _retag_unmapped(r, {"X": "value_source_unmapped"})
        assert out.indicateurs_manquants[0].reason == "value_source_unmapped"

    def test_partial_unmapped_keeps_others(self) -> None:
        r = _make_result(missing_codes=["X", "Y"])
        out = _retag_unmapped(r, {"X": "value_source_unmapped"})
        assert {m.indicateur_code: m.reason for m in out.indicateurs_manquants} == {
            "X": "value_source_unmapped",
            "Y": "value_absent",
        }


class TestSerializeDetails:
    def test_keys_present(self) -> None:
        r = _make_result(missing_codes=["X"])
        out = _serialize_details(r)
        assert set(out.keys()) == {
            "indicateurs_couverts",
            "indicateurs_manquants",
            "sources_used",
        }
        assert len(out["indicateurs_couverts"]) == 1
        c = out["indicateurs_couverts"][0]
        assert isinstance(c["indicateur_id"], str)
        assert isinstance(c["source_id"], str)

    def test_empty_result(self) -> None:
        empty = ScoreResult(
            score_global=None,
            scores_by_pillar={},
            coverage_ratio=None,
        )
        out = _serialize_details(empty)
        assert out == {
            "indicateurs_couverts": [],
            "indicateurs_manquants": [],
            "sources_used": [],
        }


class TestJsonDumps:
    def test_basic_dict(self) -> None:
        s = _json_dumps({"a": 1, "b": "two"})
        assert json.loads(s) == {"a": 1, "b": "two"}

    def test_uuid_serialized(self) -> None:
        u = uuid.uuid4()
        s = _json_dumps({"id": u})
        assert json.loads(s) == {"id": str(u)}

    def test_nested(self) -> None:
        u = uuid.uuid4()
        s = _json_dumps({"items": [{"id": u, "n": 5}]})
        assert json.loads(s) == {"items": [{"id": str(u), "n": 5}]}
