"""F48 T006 - Tests unitaires de compute_subscores (fonction pure)."""

from __future__ import annotations

from app.credit.service import compute_subscores
from app.credit.subscore_mapping import FACTOR_TO_BUCKET, SUBSCORE_BUCKETS


def _factor(name: str, value: float, weight: float) -> dict[str, object]:
    return {
        "name": name,
        "definition": "",
        "value": value,
        "weight": weight,
        "contribution": round(value * weight, 4),
        "source_id": "src",
        "axis": "solvabilite",
    }


def test_compute_subscores_returns_none_when_no_facteurs():
    assert compute_subscores(None) is None
    assert compute_subscores([]) is None


def test_compute_subscores_returns_none_when_no_mapped_factor():
    facteurs = [_factor("unknown_factor", 0.5, 0.3)]
    assert compute_subscores(facteurs) is None


def test_compute_subscores_full_mapping_in_range_0_100():
    facteurs = [
        _factor(name, 0.5, w)
        for name, (_b, w) in FACTOR_TO_BUCKET.items()
    ]
    out = compute_subscores(facteurs)
    assert out is not None
    for bucket in SUBSCORE_BUCKETS:
        v = out[bucket]
        assert v is not None
        assert 0 <= v <= 100
        # value=0.5 -> ~50/100
        assert 49 <= v <= 51


def test_compute_subscores_empty_bucket_yields_none():
    # Seulement des facteurs solidite_financiere -> autres buckets None
    facteurs = [_factor("mm_volume", 0.8, 0.35)]
    out = compute_subscores(facteurs)
    assert out is not None
    assert out["solidite_financiere"] is not None
    assert out["performance_operationnelle"] is None
    assert out["engagement_esg"] is None
    assert out["gouvernance"] is None


def test_compute_subscores_value_none_is_skipped():
    # mm_volume sans value -> bucket reste None pour solidite si seule entree
    facteurs = [
        {
            "name": "mm_volume",
            "definition": "",
            "value": None,
            "weight": 0.35,
            "contribution": 0,
            "source_id": "x",
            "axis": "solvabilite",
        },
        _factor("alignement_odd", 0.6, 1.0),
    ]
    out = compute_subscores(facteurs)
    assert out is not None
    assert out["solidite_financiere"] is None
    assert out["gouvernance"] is not None


def test_compute_subscores_unmapped_factors_ignored():
    facteurs = [
        _factor("mm_volume", 0.4, 0.35),
        _factor("totally_new_factor", 0.9, 0.5),  # ignore
    ]
    out = compute_subscores(facteurs)
    assert out is not None
    assert out["solidite_financiere"] is not None
    assert 39 <= out["solidite_financiere"] <= 41
