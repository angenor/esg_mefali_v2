"""F29 - Tests unitaires moteur credit scoring (fonctions pures)."""

from __future__ import annotations

import pytest

from app.credit.engine import (
    DEFAULT_METHODOLOGY,
    FactorDef,
    ScoringInputs,
    axis_coverage,
    coherence_warning,
    compute_combined,
    compute_factor,
    compute_factors_from_inputs,
    compute_full_score,
    compute_impact_vert,
    compute_solvabilite,
    has_esg,
    has_mobile_money,
)


def _src_map() -> dict[str, str]:
    return {spec["name"]: f"src-{spec['name']}" for spec in DEFAULT_METHODOLOGY["factors"]}


def test_compute_factor_value_present_contribution_is_value_times_weight():
    defn = FactorDef(
        name="esg_global",
        definition="d",
        weight=0.4,
        source_id="src-1",
        axis="impact_vert",
    )
    f = compute_factor(defn, 0.75)
    assert f.value == 0.75
    assert f.weight == 0.4
    assert f.contribution == 0.3
    assert f.source_id == "src-1"


def test_compute_factor_value_none_contribution_is_zero():
    defn = FactorDef(
        name="x", definition="d", weight=0.5, source_id="s", axis="solvabilite"
    )
    f = compute_factor(defn, None)
    assert f.value is None
    assert f.contribution == 0.0


def test_compute_combined_alpha_beta_default():
    assert compute_combined(80, 60) == 72


def test_compute_combined_invalid_alpha_beta():
    with pytest.raises(ValueError):
        compute_combined(50, 50, alpha=0.7, beta=0.4)
    with pytest.raises(ValueError):
        compute_combined(50, 50, alpha=-0.1, beta=1.1)


def test_compute_full_score_nominal():
    inputs = ScoringInputs(
        mm_monthly_mean_xof=500_000,
        mm_monthly_stdev_xof=50_000,
        entreprise_anciennete_years=5,
        entreprise_employes=20,
        paiements_reguliers=True,
        diversification_clients=8,
        esg_score_global=75,
        carbone_total_tco2e=200,
        nb_projets_verts=2,
        nb_odd_alignes=3,
    )
    res = compute_full_score(inputs, source_map=_src_map())
    assert 0 <= res["solvabilite"] <= 100
    assert 0 <= res["impact_vert"] <= 100
    assert 0 <= res["combine"] <= 100
    assert res["methodologie_version"] == 1
    assert res["coherence_warning"] is False
    assert len(res["facteurs"]) == len(DEFAULT_METHODOLOGY["factors"])
    for f in res["facteurs"]:
        assert f["value"] is not None
        assert f["source_id"].startswith("src-")


def test_compute_full_score_all_absent_warns():
    res = compute_full_score(ScoringInputs(), source_map=_src_map())
    assert res["solvabilite"] == 0
    assert res["impact_vert"] == 0
    assert res["combine"] == 0
    assert res["coherence_warning"] is True
    assert all(f["value"] is None and f["contribution"] == 0.0 for f in res["facteurs"])


def test_axis_coverage_partial():
    inputs = ScoringInputs(mm_monthly_mean_xof=100_000)
    factors = compute_factors_from_inputs(inputs, source_map=_src_map())
    cov_solv = axis_coverage(factors, "solvabilite")
    assert pytest.approx(cov_solv, abs=1e-6) == 0.25
    cov_imp = axis_coverage(factors, "impact_vert")
    assert cov_imp == 0


def test_coherence_warning_no_mm_no_esg_high_combine():
    inputs = ScoringInputs(
        carbone_total_tco2e=0,
        nb_projets_verts=10,
        nb_odd_alignes=10,
        entreprise_anciennete_years=10,
        entreprise_employes=50,
        paiements_reguliers=True,
        diversification_clients=10,
    )
    factors = compute_factors_from_inputs(inputs, source_map=_src_map())
    assert axis_coverage(factors, "solvabilite") >= 0.5
    assert not has_mobile_money(factors)
    assert not has_esg(factors)
    solv = compute_solvabilite(factors)
    imp = compute_impact_vert(factors)
    combine = compute_combined(solv, imp)
    if combine > 80:
        assert coherence_warning(factors, combine) is True


def test_score_axis_clamped_to_100():
    inputs = ScoringInputs(
        mm_monthly_mean_xof=10_000_000,
        mm_monthly_stdev_xof=0,
        entreprise_anciennete_years=50,
        entreprise_employes=10_000,
        paiements_reguliers=True,
        diversification_clients=100,
    )
    factors = compute_factors_from_inputs(inputs, source_map=_src_map())
    solv = compute_solvabilite(factors)
    assert 0 <= solv <= 100


def test_coverage_warning_partial_solv():
    # Couverture < 50% sur solvabilite -> warning
    inputs = ScoringInputs(
        esg_score_global=80,
        carbone_total_tco2e=100,
        nb_projets_verts=2,
        nb_odd_alignes=4,
        # solvabilite : seul mm_volume (0.25) -> 25% couverture < 50%
        mm_monthly_mean_xof=500_000,
    )
    res = compute_full_score(inputs, source_map=_src_map())
    assert res["coherence_warning"] is True
