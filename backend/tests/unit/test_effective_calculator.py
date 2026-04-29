"""F08 US4 — Tests TDD du calculateur d'effective (5 cas d'école + atomiques)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.effective_calculator import (
    compute_effective,
    compute_snapshot_hash,
    merge_criteres,
    merge_documents,
    sum_delais,
    sum_frais,
)


# Helper to forge critère dict.
def _crit(key: str, op: str, value, src=None):
    return {
        "key": key,
        "operator": op,
        "value": value,
        "unit": None,
        "source_id": str(src or uuid4()),
    }


# ---------- Atomic operator tests (T071) ----------

@pytest.mark.parametrize(
    "op,upper,lower,expected",
    [
        ("min", 1_000_000, 5_000_000, 5_000_000),
        ("max", 10_000_000, 5_000_000, 5_000_000),
    ],
)
def test_atomic_min_max(op, upper, lower, expected):
    res, w = merge_criteres([_crit("k", op, upper)], [_crit("k", op, lower)])
    assert res[0]["value"] == expected
    assert not w


def test_atomic_in_intersect():
    res, w = merge_criteres(
        [_crit("pays", "in", ["CI", "SN", "TG"])],
        [_crit("pays", "in", ["CI", "SN", "BF"])],
    )
    assert sorted(res[0]["value"]) == ["CI", "SN"]


def test_atomic_in_disjoint_emits_warning():
    res, w = merge_criteres(
        [_crit("pays", "in", ["CI"])],
        [_crit("pays", "in", ["RDC"])],
    )
    assert res[0]["value"] == []
    assert any("incompatible_countries" in x for x in w)


def test_atomic_not_in_union():
    res, _ = merge_criteres(
        [_crit("k", "not_in", ["a", "b"])],
        [_crit("k", "not_in", ["b", "c"])],
    )
    assert sorted(res[0]["value"]) == ["a", "b", "c"]


def test_atomic_eq_diverge_warning():
    _res, w = merge_criteres(
        [_crit("k", "eq", "X")],
        [_crit("k", "eq", "Y")],
    )
    assert any("eq_value_diverges" in x for x in w)


def test_atomic_contains_intersect():
    res, _ = merge_criteres(
        [_crit("k", "contains", ["a", "b", "c"])],
        [_crit("k", "contains", ["b", "c", "d"])],
    )
    assert sorted(res[0]["value"]) == ["b", "c"]


# ---------- Documents (T072) ----------

def test_documents_union_by_id():
    docs = merge_documents(
        [{"document_id": "d1", "label": "L1", "type": "financier", "required": True}],
        [
            {"document_id": "d1", "label": "L1bis", "type": "financier", "required": True},
            {"document_id": "d2", "label": "L2", "type": "esg", "required": True},
        ],
        [{"document_id": "d3", "label": "L3", "type": "autre", "required": False}],
    )
    ids = sorted(d["document_id"] for d in docs)
    assert ids == ["d1", "d2", "d3"]
    # Last wins for d1
    d1 = next(d for d in docs if d["document_id"] == "d1")
    assert d1["label"] == "L1bis"


# ---------- Frais & délais (T072) ----------

def test_sum_frais_same_currency():
    out, w = sum_frais(
        {"origination_pct": 1.0, "currency": "EUR"},
        {"origination_pct": 0.5, "currency": "EUR"},
        {"marge_pct": 0.2, "currency": "EUR"},
    )
    assert out["origination_pct"] == 1.5
    assert out["marge_pct"] == 0.2
    assert not w


def test_sum_frais_mixed_currency_warning():
    _out, w = sum_frais(
        {"origination_pct": 1.0, "currency": "EUR"},
        {"origination_pct": 0.5, "currency": "USD"},
    )
    assert "mixed_currency_fees" in w


def test_sum_delais():
    out = sum_delais(
        {"instruction_jours": 30, "decaissement_jours": 60},
        {"instruction_jours": 10},
        {"decaissement_jours": 5},
    )
    assert out["instruction_jours"] == 40
    assert out["decaissement_jours"] == 65


# ---------- Snapshot hash determinism ----------

def test_snapshot_hash_stable():
    h1 = compute_snapshot_hash({"a": 1, "b": [1, 2]})
    h2 = compute_snapshot_hash({"b": [1, 2], "a": 1})
    assert h1 == h2


# ---------- 5 cas d'école (T070) ----------

@pytest.mark.parametrize(
    "case,fonds,inter,offre,expected_value,expected_warning",
    [
        # Cas 1 : GCF (max 10M USD) × BOAD (max 5M USD) → 5M USD
        (
            "gcf_boad_min_project_size",
            {"criteres_json": [_crit("max_project_size", "max", 10_000_000)],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_json": [_crit("max_project_size", "max", 5_000_000)],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_offre_specifiques": [], "documents_specifiques": [],
             "frais_specifiques": {}, "delais_specifiques": {}, "accepted_languages": ["fr"]},
            5_000_000,
            None,
        ),
        # Cas 2 : GCF (CI,SN,TG) × UNDP (CI,SN,BF) → intersect {CI,SN}
        (
            "gcf_undp_pays",
            {"criteres_json": [_crit("pays", "in", ["CI", "SN", "TG"])],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_json": [_crit("pays", "in", ["CI", "SN", "BF"])],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_offre_specifiques": [], "documents_specifiques": [],
             "frais_specifiques": {}, "delais_specifiques": {}, "accepted_languages": ["fr"]},
            ["CI", "SN"],
            None,
        ),
        # Cas 3 : FEM (don, prêt) × PNUD (don, garantie) → intersect {don}
        (
            "fem_pnud_instruments",
            {"criteres_json": [_crit("instruments", "in", ["don", "pret"])],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_json": [_crit("instruments", "in", ["don", "garantie"])],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_offre_specifiques": [], "documents_specifiques": [],
             "frais_specifiques": {}, "delais_specifiques": {}, "accepted_languages": ["fr"]},
            ["don"],
            None,
        ),
        # Cas 4 : SUNREF (max 10M EUR) × Ecobank (max 5M EUR) → 5M
        (
            "sunref_ecobank_max_amount",
            {"criteres_json": [_crit("max_amount", "max", 10_000_000)],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_json": [_crit("max_amount", "max", 5_000_000)],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_offre_specifiques": [], "documents_specifiques": [],
             "frais_specifiques": {}, "delais_specifiques": {}, "accepted_languages": ["fr"]},
            5_000_000,
            None,
        ),
        # Cas 5 : FNE-CI (CI seul) × banque RDC (RDC seul) → vide + warning
        (
            "fneci_banque_rdc_incompat",
            {"criteres_json": [_crit("pays", "in", ["CI"])],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_json": [_crit("pays", "in", ["RDC"])],
             "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
            {"criteres_offre_specifiques": [], "documents_specifiques": [],
             "frais_specifiques": {}, "delais_specifiques": {}, "accepted_languages": ["fr"]},
            [],
            "incompatible_countries",
        ),
    ],
)
def test_five_canonical_cases(case, fonds, inter, offre, expected_value, expected_warning):
    res = compute_effective(fonds, inter, offre)
    crit = res["criteres_effectifs"][0]
    assert crit["value"] == expected_value, f"case {case}"
    if expected_warning:
        assert any(expected_warning in w for w in res["effective_warning"]), f"case {case}"
    else:
        assert all("incompatible" not in w for w in res["effective_warning"]), f"case {case}"


def test_compute_effective_offre_deadline_overrides():
    res = compute_effective(
        {"deadline": "2026-01-01", "criteres_json": [], "documents_requis_json": [],
         "frais_json": {}, "delais_json": {}},
        {"criteres_json": [], "documents_requis_json": [], "frais_json": {}, "delais_json": {}},
        {"deadline": "2026-09-30", "criteres_offre_specifiques": [],
         "documents_specifiques": [], "frais_specifiques": {},
         "delais_specifiques": {}, "accepted_languages": ["fr"]},
    )
    assert str(res["deadline"]) == "2026-09-30"
