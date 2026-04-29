"""F11 T012 — Complétude profil entreprise."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.entreprise.completeness import (
    FEATURE_REQUIREMENTS,
    GLOBAL_FIELDS,
    compute_missing_per_feature,
    compute_percentage,
)


@pytest.mark.unit
class TestCompleteness:
    def test_empty_profile_is_zero_pct(self) -> None:
        assert compute_percentage({}) == 0

    def test_partial_profile(self) -> None:
        profile = {"name": "Acme", "secteur_code": "agro_elevage"}
        pct = compute_percentage(profile)
        expected = int(round(100 * 2 / len(GLOBAL_FIELDS)))
        assert pct == expected

    def test_full_profile_is_100(self) -> None:
        profile = {
            "name": "Acme SARL",
            "secteur_code": "agro_elevage",
            "taille_ca": {"amount": Decimal("1"), "currency": "XOF"},
            "taille_effectifs": 12,
            "localisation_siege_pays_iso2": "CI",
            "localisation_siege_ville": "Abidjan",
            "zones_operation_pays_iso2": ["CI"],
            "gouvernance_json": {"forme": "SARL"},
            "pratiques_actuelles_json": {"recyclage": True},
        }
        assert compute_percentage(profile) == 100

    def test_missing_per_feature_empty_profile(self) -> None:
        result = compute_missing_per_feature({})
        feature_codes = {x["feature_code"] for x in result}
        for req in FEATURE_REQUIREMENTS:
            assert req.feature_code in feature_codes
        for entry in result:
            assert entry["missing_fields"]

    def test_missing_per_feature_filled_for_esg(self) -> None:
        profile = {
            "secteur_code": "agro_elevage",
            "taille_effectifs": 12,
            "taille_ca": {"amount": Decimal("1"), "currency": "XOF"},
        }
        result = compute_missing_per_feature(profile)
        esg = next(x for x in result if x["feature_code"] == "esg_scoring")
        assert esg["missing_fields"] == []

    def test_zero_value_effectifs_is_filled(self) -> None:
        assert compute_percentage({"taille_effectifs": 0}) > 0
