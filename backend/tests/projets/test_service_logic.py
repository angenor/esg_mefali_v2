"""F12 - Tests unitaires de la logique pure du service (sans DB)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.projets.service import (
    DeleteProtected,
    ProjetRow,
    VersionConflict,
    _diff,
    _jsonable,
    aggregate_read,
    aggregate_summary,
)


def _make_row(**overrides) -> ProjetRow:
    base = {
        "id": uuid4(),
        "account_id": uuid4(),
        "entreprise_id": uuid4(),
        "version": 1,
        "nom": "Eolien",
        "description": "desc",
        "objectif_environnemental": "obj",
        "types_impact": ["mitigation_carbone"],
        "maturite": "pilote",
        "montant_recherche_amount": Decimal("1000"),
        "montant_recherche_currency": "XOF",
        "duree_mois": 12,
        "structure_financement_arr": ["subvention"],
        "indicateurs_impact_json": [{"key": "k", "value": 1, "unit": "u"}],
        "localisation_pays_iso2": "CI",
        "localisation_ville": "Abidjan",
        "statut": "brouillon",
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 2),
    }
    base.update(overrides)
    return ProjetRow(**base)


class TestDiff:
    def test_no_change(self):
        row = _make_row()
        assert _diff(row, {"nom": "Eolien"}) == {}

    def test_simple_change(self):
        row = _make_row()
        d = _diff(row, {"nom": "Eolien++"})
        assert "nom" in d
        assert d["nom"][0] == "Eolien"
        assert d["nom"][1] == "Eolien++"

    def test_money_change(self):
        row = _make_row()
        d = _diff(row, {"montant_recherche": {"amount": "2000", "currency": "XOF"}})
        assert "montant_recherche" in d

    def test_money_set_none(self):
        row = _make_row()
        d = _diff(row, {"montant_recherche": None})
        assert "montant_recherche" in d

    def test_money_no_change(self):
        row = _make_row()
        d = _diff(row, {"montant_recherche": {"amount": "1000", "currency": "XOF"}})
        assert d == {}

    def test_unknown_key_ignored(self):
        row = _make_row()
        d = _diff(row, {"weird": "x"})
        assert d == {}

    def test_array_change(self):
        row = _make_row()
        d = _diff(row, {"types_impact": ["adaptation"]})
        assert "types_impact" in d


class TestAggregates:
    def test_aggregate_read(self):
        row = _make_row()
        out = aggregate_read(row)
        assert out["nom"] == "Eolien"
        assert out["montant_recherche"]["currency"] == "XOF"
        assert out["statut"] == "brouillon"

    def test_aggregate_read_none_money(self):
        row = _make_row(montant_recherche_amount=None, montant_recherche_currency=None)
        out = aggregate_read(row)
        assert out["montant_recherche"] is None

    def test_aggregate_summary(self):
        row = _make_row()
        out = aggregate_summary(row)
        assert out["nom"] == "Eolien"
        assert "description" not in out


class TestJsonable:
    def test_decimal(self):
        assert _jsonable(Decimal("1.5")) == "1.5"

    def test_none(self):
        assert _jsonable(None) is None

    def test_dict(self):
        out = _jsonable({"a": Decimal("2"), "b": [Decimal("3")]})
        assert out == {"a": "2", "b": ["3"]}

    def test_list(self):
        assert _jsonable([Decimal("1"), 2]) == ["1", 2]

    def test_passthrough(self):
        assert _jsonable("hello") == "hello"


class TestExceptions:
    def test_version_conflict(self):
        e = VersionConflict(5, 3)
        assert e.current_version == 5
        assert e.your_version == 3
        assert "current=5" in str(e)

    def test_delete_protected(self):
        e = DeleteProtected("finance")
        assert e.statut == "finance"
        assert "X-Confirm" in str(e)
