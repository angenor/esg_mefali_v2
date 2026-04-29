"""F23 — Tests unitaires du moteur de scoring weighted_sum."""

from __future__ import annotations

import uuid

import pytest

from app.scoring.engine import IndicatorRule, compute_score

_UNSET = object()


def _rule(
    code: str,
    pillar: str = "E",
    value_type: str = "numeric",
    weight: float = 1.0,
    seuil_min: int | None = None,
    seuil_max: int | None = None,
    enum_values: list | None = None,
    source_id=_UNSET,
) -> IndicatorRule:
    resolved_source = uuid.uuid4() if source_id is _UNSET else source_id
    return IndicatorRule(
        indicateur_id=uuid.uuid4(),
        indicateur_code=code,
        pillar=pillar,
        value_type=value_type,
        weight=weight,
        source_id=resolved_source,
        seuil_min=seuil_min,
        seuil_max=seuil_max,
        enum_values=enum_values,
    )


class TestWeightedSum:
    def test_three_covered_normalized(self) -> None:
        rules = [
            _rule("A", pillar="E", weight=1.0, seuil_min=0, seuil_max=100),
            _rule("B", pillar="S", weight=1.0, seuil_min=0, seuil_max=100),
            _rule("C", pillar="G", weight=2.0, seuil_min=0, seuil_max=100),
        ]
        values = {"A": 80, "B": 60, "C": 40}
        result = compute_score(rules=rules, values=values)
        # (1*80 + 1*60 + 2*40) / 4 = 220/4 = 55
        assert result.score_global == 55.0
        assert result.scores_by_pillar == {"E": 80.0, "S": 60.0, "G": 40.0}
        assert len(result.indicateurs_couverts) == 3
        assert len(result.indicateurs_manquants) == 0
        assert result.coverage_ratio == 1.0

    def test_partial_coverage(self) -> None:
        rules = [
            _rule("A", pillar="E", weight=1.0, seuil_min=0, seuil_max=100),
            _rule("B", pillar="S", weight=1.0, seuil_min=0, seuil_max=100),
            _rule("C", pillar="G", weight=2.0, seuil_min=0, seuil_max=100),
        ]
        values = {"A": 80}  # B et C absents
        result = compute_score(rules=rules, values=values)
        assert result.score_global == 80.0
        assert result.scores_by_pillar == {"E": 80.0}
        assert len(result.indicateurs_manquants) == 2
        assert result.coverage_ratio == 0.25  # 1/4

    def test_no_coverage(self) -> None:
        rules = [
            _rule("A", pillar="E", weight=1.0, seuil_min=0, seuil_max=100),
        ]
        result = compute_score(rules=rules, values={})
        assert result.score_global is None
        assert result.scores_by_pillar == {}
        assert result.coverage_ratio == 0.0
        assert len(result.indicateurs_manquants) == 1
        assert result.indicateurs_manquants[0].reason == "value_absent"

    def test_zero_total_weight(self) -> None:
        # Tous les poids ≤ 0 → score_global = None.
        rules = [
            _rule("A", weight=0.0, seuil_min=0, seuil_max=100),
        ]
        result = compute_score(rules=rules, values={"A": 50})
        assert result.score_global is None
        assert result.coverage_ratio is None

    def test_misconfig_no_source_id(self) -> None:
        rules = [_rule("A", weight=1.0, source_id=None)]
        result = compute_score(rules=rules, values={"A": 50})
        assert len(result.indicateurs_manquants) == 1
        assert (
            result.indicateurs_manquants[0].reason
            == "referentiel_indicateur_misconfig"
        )

    def test_pillar_with_no_covered_indicator(self) -> None:
        rules = [
            _rule("A", pillar="E", weight=1.0, seuil_min=0, seuil_max=100),
            _rule("B", pillar="S", weight=1.0, seuil_min=0, seuil_max=100),
        ]
        # Seul E couvert, S absent → S absent du dict (pas zéro).
        result = compute_score(rules=rules, values={"A": 80})
        assert result.scores_by_pillar == {"E": 80.0}
        assert "S" not in result.scores_by_pillar

    def test_determinism(self) -> None:
        rules = [
            _rule("A", weight=1.5, seuil_min=0, seuil_max=100),
            _rule("B", pillar="S", value_type="boolean", weight=2.0),
        ]
        values = {"A": 70, "B": True}
        r1 = compute_score(rules=rules, values=values)
        r2 = compute_score(rules=rules, values=values)
        assert r1.score_global == r2.score_global
        assert r1.scores_by_pillar == r2.scores_by_pillar

    def test_sources_used_dedup(self) -> None:
        shared = uuid.uuid4()
        rules = [
            _rule("A", weight=1.0, source_id=shared, seuil_min=0, seuil_max=100),
            _rule(
                "B",
                pillar="S",
                weight=1.0,
                source_id=shared,
                seuil_min=0,
                seuil_max=100,
            ),
        ]
        result = compute_score(rules=rules, values={"A": 50, "B": 50})
        assert result.sources_used == [shared]

    def test_unsupported_value_type_marks_missing(self) -> None:
        rules = [_rule("A", value_type="text", weight=1.0)]
        result = compute_score(rules=rules, values={"A": "hello"})
        assert len(result.indicateurs_manquants) == 1
        assert (
            result.indicateurs_manquants[0].reason == "unsupported_value_type"
        )
        assert result.score_global is None


class TestCoveredIndicatorPayload:
    def test_contribution_calc(self) -> None:
        rules = [_rule("A", weight=2.0, seuil_min=0, seuil_max=100)]
        result = compute_score(rules=rules, values={"A": 50})
        assert len(result.indicateurs_couverts) == 1
        c = result.indicateurs_couverts[0]
        assert c.normalized_value == 50.0
        assert c.weight == 2.0
        assert c.contribution == pytest.approx(100.0)
        assert c.source_id is not None
