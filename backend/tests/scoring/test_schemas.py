"""F23 — Tests unitaires des schémas Pydantic /me/scoring."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.scoring.schemas import (
    CoveredIndicatorOut,
    MissingIndicatorOut,
    ScoreDetailOut,
    ScoreListOut,
    ScoreSummaryOut,
)


def _summary_kwargs() -> dict:
    return {
        "referentiel_code": "ESG_MEFALI",
        "referentiel_id": uuid.uuid4(),
        "referentiel_version": 1,
        "score_global": 75.0,
        "scores_by_pillar": {"E": 80.0, "S": 70.0, "G": None},
        "coverage_ratio": 0.8,
        "computed_at": datetime.now(UTC),
    }


class TestScoreSummary:
    def test_minimal(self) -> None:
        m = ScoreSummaryOut(**_summary_kwargs())
        assert m.referentiel_code == "ESG_MEFALI"
        assert m.score_global == 75.0

    def test_score_null(self) -> None:
        kw = _summary_kwargs()
        kw["score_global"] = None
        kw["coverage_ratio"] = None
        m = ScoreSummaryOut(**kw)
        assert m.score_global is None

    def test_extra_forbidden(self) -> None:
        from pydantic import ValidationError

        kw = _summary_kwargs()
        kw["unexpected_field"] = "boom"
        with pytest.raises(ValidationError):
            ScoreSummaryOut(**kw)


class TestScoreDetail:
    def test_with_lists(self) -> None:
        kw = _summary_kwargs()
        kw["indicateurs_couverts"] = [
            CoveredIndicatorOut(
                indicateur_id=uuid.uuid4(),
                indicateur_code="A",
                pillar="E",
                value=42,
                normalized_value=70.0,
                weight=1.0,
                contribution=70.0,
                source_id=uuid.uuid4(),
            )
        ]
        kw["indicateurs_manquants"] = [
            MissingIndicatorOut(
                indicateur_id=uuid.uuid4(),
                indicateur_code="B",
                pillar="S",
                reason="value_absent",
            )
        ]
        kw["sources_used"] = [uuid.uuid4()]
        m = ScoreDetailOut(**kw)
        assert len(m.indicateurs_couverts) == 1
        assert m.indicateurs_manquants[0].reason == "value_absent"
        assert len(m.sources_used) == 1

    def test_default_empty_lists(self) -> None:
        m = ScoreDetailOut(**_summary_kwargs())
        assert m.indicateurs_couverts == []
        assert m.indicateurs_manquants == []
        assert m.sources_used == []


class TestScoreList:
    def test_empty(self) -> None:
        m = ScoreListOut(entity_type="entreprise", entity_id=uuid.uuid4())
        assert m.scores == []

    def test_with_one(self) -> None:
        s = ScoreSummaryOut(**_summary_kwargs())
        m = ScoreListOut(entity_type="entreprise", entity_id=uuid.uuid4(), scores=[s])
        assert len(m.scores) == 1
        assert m.scores[0].referentiel_code == "ESG_MEFALI"
