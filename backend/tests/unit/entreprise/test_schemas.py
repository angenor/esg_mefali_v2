"""F11 T010 — Pydantic schemas validation."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.entreprise.schemas import EntreprisePatchIn, MoneyIn


@pytest.mark.unit
class TestSchemas:
    def test_effectifs_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EntreprisePatchIn(taille_effectifs=-1)

    def test_effectifs_too_high_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EntreprisePatchIn(taille_effectifs=10001)

    def test_effectifs_ok(self) -> None:
        m = EntreprisePatchIn(taille_effectifs=75)
        assert m.taille_effectifs == 75

    def test_money_invalid_currency(self) -> None:
        with pytest.raises(ValidationError):
            MoneyIn(amount=Decimal("100"), currency="ABC")

    def test_money_xof_ok(self) -> None:
        m = MoneyIn(amount=Decimal("250000000"), currency="xof")
        assert m.currency == "XOF"

    def test_money_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MoneyIn(amount=Decimal("-1"), currency="XOF")

    def test_iso2_unknown_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EntreprisePatchIn(localisation_siege_pays_iso2="FR")

    def test_iso2_uemoa_ok(self) -> None:
        m = EntreprisePatchIn(localisation_siege_pays_iso2="ci")
        assert m.localisation_siege_pays_iso2 == "CI"

    def test_secteur_code_unknown_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EntreprisePatchIn(secteur_code="not_a_sector")

    def test_secteur_code_known_ok(self) -> None:
        m = EntreprisePatchIn(secteur_code="agro_elevage")
        assert m.secteur_code == "agro_elevage"

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EntreprisePatchIn(unknown_field="x")

    def test_zones_validates_each(self) -> None:
        with pytest.raises(ValidationError):
            EntreprisePatchIn(zones_operation_pays_iso2=["CI", "FR"])

    def test_zones_ok(self) -> None:
        m = EntreprisePatchIn(zones_operation_pays_iso2=["ci", "sn"])
        assert m.zones_operation_pays_iso2 == ["CI", "SN"]
