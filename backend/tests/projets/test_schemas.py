"""F12 - Tests Pydantic schemas."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.projets.schemas import (
    MoneyIn,
    ProjetCreate,
    ProjetPatch,
    TransitionIn,
)


class TestMoneyIn:
    def test_xof_ok(self):
        m = MoneyIn(amount=Decimal("100"), currency="XOF")
        assert m.currency == "XOF"

    def test_lower_normalised(self):
        m = MoneyIn(amount=Decimal("100"), currency="eur")
        assert m.currency == "EUR"

    def test_unknown_currency(self):
        with pytest.raises(ValidationError):
            MoneyIn(amount=Decimal("1"), currency="JPY")

    def test_negative_amount(self):
        with pytest.raises(ValidationError):
            MoneyIn(amount=Decimal("-1"), currency="EUR")


class TestProjetCreate:
    def test_minimum(self):
        p = ProjetCreate(nom="Mon projet")
        assert p.nom == "Mon projet"
        assert p.statut is None

    def test_full(self):
        p = ProjetCreate(
            nom="Eolien rural",
            description="x",
            objectif_environnemental="reduire CO2",
            types_impact=["mitigation_carbone", "energies_renouvelables"],
            maturite="pilote",
            montant_recherche={"amount": "1000000", "currency": "XOF"},
            duree_mois=24,
            structure_financement_arr=["subvention", "blending"],
            indicateurs_impact_json=[{"key": "tCO2e", "value": 100, "unit": "tCO2e/an"}],
            localisation_pays_iso2="ci",
            localisation_ville="Abidjan",
            statut="brouillon",
        )
        assert p.localisation_pays_iso2 == "CI"
        assert p.duree_mois == 24

    def test_invalid_types_impact(self):
        with pytest.raises(ValidationError):
            ProjetCreate(nom="x", types_impact=["weird"])

    def test_invalid_structure(self):
        with pytest.raises(ValidationError):
            ProjetCreate(nom="x", structure_financement_arr=["loan"])

    def test_invalid_statut(self):
        with pytest.raises(ValidationError):
            ProjetCreate(nom="x", statut="xyz")

    def test_invalid_maturite(self):
        with pytest.raises(ValidationError):
            ProjetCreate(nom="x", maturite="zzz")

    def test_invalid_pays_iso2(self):
        with pytest.raises(ValidationError):
            ProjetCreate(nom="x", localisation_pays_iso2="123")

    def test_duree_negative(self):
        with pytest.raises(ValidationError):
            ProjetCreate(nom="x", duree_mois=-1)

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError):
            ProjetCreate(nom="x", unknown_field="oops")


class TestProjetPatch:
    def test_all_optional(self):
        p = ProjetPatch()
        assert p.nom is None


class TestTransitionIn:
    def test_valid(self):
        t = TransitionIn(to="finance")
        assert t.to == "finance"

    def test_invalid(self):
        with pytest.raises(ValidationError):
            TransitionIn(to="rejected")
