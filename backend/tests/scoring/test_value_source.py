"""F23 — Tests unitaires de la résolution valeurs PME."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.scoring.value_source import (
    VALUE_SOURCE_MAP,
    collect_values,
    resolve_value,
)


@dataclass
class FakeEntreprise:
    taille_effectifs: int | None = None
    taille_ca_amount: Any = None
    localisation_siege_pays_iso2: str | None = None
    gouvernance_json: dict | None = None
    pratiques_actuelles_json: dict | None = None


class TestResolve:
    def test_direct_attribute(self) -> None:
        ent = FakeEntreprise(taille_effectifs=42)
        v, reason = resolve_value(indicateur_code="EFFECTIFS_TOTAL", entreprise=ent)
        assert reason is None
        assert v == 42

    def test_attribute_none(self) -> None:
        ent = FakeEntreprise()
        v, reason = resolve_value(indicateur_code="EFFECTIFS_TOTAL", entreprise=ent)
        assert reason is None
        assert v is None

    def test_unmapped_code(self) -> None:
        ent = FakeEntreprise()
        v, reason = resolve_value(indicateur_code="UNKNOWN_CODE_XYZ", entreprise=ent)
        assert reason == "value_source_unmapped"
        assert v is None

    def test_jsonb_extraction(self) -> None:
        ent = FakeEntreprise(gouvernance_json={"audit_interne": True})
        v, reason = resolve_value(
            indicateur_code="GOUVERNANCE_AUDIT_INTERNE", entreprise=ent
        )
        assert reason is None
        assert v is True

    def test_jsonb_missing_key(self) -> None:
        ent = FakeEntreprise(gouvernance_json={"other": 1})
        v, reason = resolve_value(
            indicateur_code="GOUVERNANCE_AUDIT_INTERNE", entreprise=ent
        )
        assert reason is None
        assert v is None

    def test_jsonb_missing_field(self) -> None:
        ent = FakeEntreprise()
        v, reason = resolve_value(
            indicateur_code="GOUVERNANCE_AUDIT_INTERNE", entreprise=ent
        )
        assert reason is None
        assert v is None

    def test_dict_entreprise(self) -> None:
        ent = {"taille_effectifs": 99}
        v, reason = resolve_value(indicateur_code="EFFECTIFS_TOTAL", entreprise=ent)
        assert v == 99
        assert reason is None

    def test_none_entreprise(self) -> None:
        v, reason = resolve_value(indicateur_code="EFFECTIFS_TOTAL", entreprise=None)
        assert reason is None
        assert v is None


class TestCollectValues:
    def test_split_mapped_unmapped(self) -> None:
        ent = FakeEntreprise(taille_effectifs=10, taille_ca_amount=500_000)
        codes = ["EFFECTIFS_TOTAL", "CA_AMOUNT", "BOGUS_CODE"]
        values, unmapped = collect_values(indicateur_codes=codes, entreprise=ent)
        assert values == {"EFFECTIFS_TOTAL": 10, "CA_AMOUNT": 500_000}
        assert unmapped == {"BOGUS_CODE": "value_source_unmapped"}

    def test_empty_codes(self) -> None:
        ent = FakeEntreprise()
        values, unmapped = collect_values(indicateur_codes=[], entreprise=ent)
        assert values == {}
        assert unmapped == {}


class TestMapStability:
    def test_demo_codes_present(self) -> None:
        for code in ("DEMO_E1", "DEMO_S1", "DEMO_G1"):
            assert code in VALUE_SOURCE_MAP
