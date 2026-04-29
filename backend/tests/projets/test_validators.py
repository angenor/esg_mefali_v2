"""F12 - Tests unitaires des validators."""

from __future__ import annotations

import pytest

from app.projets.validators import (
    MAX_DOC_SIZE_BYTES,
    ValidationError,
    validate_doc_type,
    validate_indicateurs,
    validate_maturite,
    validate_mime,
    validate_size,
    validate_statut,
    validate_structure_financement,
    validate_types_impact,
)


class TestIndicateurs:
    def test_none_returns_empty_list(self):
        assert validate_indicateurs(None) == []

    def test_valid_list(self):
        out = validate_indicateurs([
            {"key": "tCO2e", "value": 1500, "unit": "tCO2e/an"},
            {"key": "emplois", "value": 25.5, "unit": "ETP"},
        ])
        assert len(out) == 2
        assert out[0]["key"] == "tCO2e"
        assert out[1]["value"] == 25.5

    def test_not_a_list(self):
        with pytest.raises(ValidationError) as exc:
            validate_indicateurs({"key": "x"})
        assert exc.value.code == "indicateurs_invalid"

    def test_item_not_dict(self):
        with pytest.raises(ValidationError) as exc:
            validate_indicateurs(["a"])
        assert "item" in exc.value.code

    def test_missing_key(self):
        with pytest.raises(ValidationError) as exc:
            validate_indicateurs([{"key": "", "value": 1, "unit": "x"}])
        assert exc.value.code == "indicateurs_invalid_key"

    def test_value_not_numeric(self):
        with pytest.raises(ValidationError) as exc:
            validate_indicateurs([{"key": "k", "value": "abc", "unit": "x"}])
        assert exc.value.code == "indicateurs_invalid_value"

    def test_value_bool_rejected(self):
        with pytest.raises(ValidationError):
            validate_indicateurs([{"key": "k", "value": True, "unit": "x"}])

    def test_missing_unit(self):
        with pytest.raises(ValidationError) as exc:
            validate_indicateurs([{"key": "k", "value": 1, "unit": ""}])
        assert exc.value.code == "indicateurs_invalid_unit"


class TestMime:
    def test_valid(self):
        assert validate_mime("application/pdf") == "application/pdf"

    def test_invalid(self):
        with pytest.raises(ValidationError) as exc:
            validate_mime("application/x-evil")
        assert exc.value.code == "mime_not_allowed"


class TestSize:
    def test_valid(self):
        assert validate_size(1024) == 1024

    def test_zero(self):
        with pytest.raises(ValidationError):
            validate_size(0)

    def test_negative(self):
        with pytest.raises(ValidationError):
            validate_size(-1)

    def test_too_large(self):
        with pytest.raises(ValidationError) as exc:
            validate_size(MAX_DOC_SIZE_BYTES + 1)
        assert exc.value.code == "size_too_large"


class TestDocType:
    @pytest.mark.parametrize("t", [
        "faisabilite", "business_plan", "etude_impact",
        "lettre_soutien", "photo", "autre",
    ])
    def test_valid(self, t):
        assert validate_doc_type(t) == t

    def test_invalid(self):
        with pytest.raises(ValidationError):
            validate_doc_type("evil")


class TestEnums:
    def test_types_impact_ok(self):
        assert validate_types_impact(["mitigation_carbone", "eau"]) == ["mitigation_carbone", "eau"]

    def test_types_impact_invalid(self):
        with pytest.raises(ValidationError):
            validate_types_impact(["weird"])

    def test_types_impact_none(self):
        assert validate_types_impact(None) is None

    def test_structure_ok(self):
        assert validate_structure_financement(["subvention"]) == ["subvention"]

    def test_structure_invalid(self):
        with pytest.raises(ValidationError):
            validate_structure_financement(["loan"])

    def test_statut_ok(self):
        assert validate_statut("brouillon") == "brouillon"

    def test_statut_none(self):
        assert validate_statut(None) is None

    def test_statut_invalid(self):
        with pytest.raises(ValidationError):
            validate_statut("xyz")

    def test_maturite_ok(self):
        assert validate_maturite("pilote") == "pilote"

    def test_maturite_invalid(self):
        with pytest.raises(ValidationError):
            validate_maturite("zzz")
