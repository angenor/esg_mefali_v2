"""F11 T011 — Taxonomie sectorielle."""

from __future__ import annotations

import pytest

from app.entreprise.taxonomy import (
    ALLOWED_CURRENCIES,
    SECTORS,
    UEMOA_CEDEAO_ISO2,
    all_sector_codes,
    get_sector,
)


@pytest.mark.unit
class TestTaxonomy:
    def test_sectors_size(self) -> None:
        assert len(SECTORS) >= 30

    def test_sector_codes_unique(self) -> None:
        codes = [s.code for s in SECTORS]
        assert len(codes) == len(set(codes))

    def test_sector_labels_non_empty(self) -> None:
        for s in SECTORS:
            assert s.label.strip()

    def test_get_sector_returns_label(self) -> None:
        s = get_sector("agro_culture_vivriere")
        assert s is not None
        assert "Agriculture" in s.label

    def test_get_sector_unknown(self) -> None:
        assert get_sector("__not_a_real_sector__") is None

    def test_all_codes_set(self) -> None:
        codes = all_sector_codes()
        assert isinstance(codes, frozenset)
        assert len(codes) == len(SECTORS)

    def test_uemoa_cedeao_minimum(self) -> None:
        for c in ("BJ", "BF", "CI", "ML", "NE", "SN", "TG", "GH", "NG"):
            assert c in UEMOA_CEDEAO_ISO2

    def test_currencies(self) -> None:
        assert {"XOF", "EUR", "USD"} == set(ALLOWED_CURRENCIES)
