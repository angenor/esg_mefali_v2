"""F23 — Tests unitaires de la normalisation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.scoring.normalizer import normalize_value


class TestNumeric:
    def test_with_seuils_linear(self) -> None:
        r = normalize_value(value=50, value_type="numeric", seuil_min=0, seuil_max=100)
        assert r.is_covered
        assert r.value == 50.0

    def test_with_seuils_clamp_high(self) -> None:
        r = normalize_value(value=200, value_type="numeric", seuil_min=0, seuil_max=100)
        assert r.value == 100.0

    def test_with_seuils_clamp_low(self) -> None:
        r = normalize_value(value=-10, value_type="numeric", seuil_min=0, seuil_max=100)
        assert r.value == 0.0

    def test_with_seuils_decimal_input(self) -> None:
        r = normalize_value(
            value=Decimal("25"),
            value_type="numeric",
            seuil_min=Decimal("0"),
            seuil_max=Decimal("50"),
        )
        assert r.value == 50.0

    def test_without_seuils_clamps(self) -> None:
        r = normalize_value(value=42, value_type="numeric")
        assert r.value == 42.0

    def test_without_seuils_clamps_high(self) -> None:
        r = normalize_value(value=999, value_type="numeric")
        assert r.value == 100.0

    def test_invalid_value_string(self) -> None:
        r = normalize_value(value="not_a_number", value_type="numeric")
        assert not r.is_covered
        assert r.reason == "invalid_value"

    def test_misconfig_seuils_inverted(self) -> None:
        r = normalize_value(value=50, value_type="numeric", seuil_min=100, seuil_max=0)
        assert r.reason == "referentiel_indicateur_misconfig"


class TestBoolean:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (True, 100.0),
            (False, 0.0),
            (1, 100.0),
            (0, 0.0),
            ("true", 100.0),
            ("FALSE", 0.0),
            ("oui", 100.0),
            ("non", 0.0),
        ],
    )
    def test_truthy(self, raw, expected) -> None:
        r = normalize_value(value=raw, value_type="boolean")
        assert r.is_covered
        assert r.value == expected

    def test_invalid_string(self) -> None:
        r = normalize_value(value="peut-etre", value_type="boolean")
        assert r.reason == "invalid_value"


class TestEnum:
    def test_first(self) -> None:
        r = normalize_value(value="A", value_type="enum", enum_values=["A", "B", "C"])
        assert r.value == 0.0

    def test_last(self) -> None:
        r = normalize_value(value="C", value_type="enum", enum_values=["A", "B", "C"])
        assert r.value == 100.0

    def test_middle(self) -> None:
        r = normalize_value(value="B", value_type="enum", enum_values=["A", "B", "C"])
        assert r.value == 50.0

    def test_unknown_value(self) -> None:
        r = normalize_value(value="X", value_type="enum", enum_values=["A", "B"])
        assert r.reason == "invalid_value"

    def test_no_enum_values(self) -> None:
        r = normalize_value(value="A", value_type="enum", enum_values=None)
        assert r.reason == "referentiel_indicateur_misconfig"

    def test_empty_enum_values(self) -> None:
        r = normalize_value(value="A", value_type="enum", enum_values=[])
        assert r.reason == "referentiel_indicateur_misconfig"

    def test_single_value(self) -> None:
        r = normalize_value(value="X", value_type="enum", enum_values=["X"])
        assert r.value == 100.0


class TestUnsupportedAndAbsent:
    def test_value_absent(self) -> None:
        r = normalize_value(value=None, value_type="numeric")
        assert r.reason == "value_absent"

    def test_text_unsupported(self) -> None:
        r = normalize_value(value="hello", value_type="text")
        assert r.reason == "unsupported_value_type"

    def test_json_unsupported(self) -> None:
        r = normalize_value(value={"a": 1}, value_type="json")
        assert r.reason == "unsupported_value_type"
