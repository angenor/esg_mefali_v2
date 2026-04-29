"""F12 - Tests service.py with a fake SQLAlchemy session.

We do not connect to Postgres; we simulate `db.execute(...)` results
using a custom fake to drive coverage on SQL-construction paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from app.projets import service as srv


@dataclass
class FakeRow:
    """Mimics a Row object accessed via attributes."""
    id: Any = None
    account_id: Any = None
    entreprise_id: Any = None
    version: int = 1
    nom: str = "n"
    description: str | None = None
    objectif_environnemental: str | None = None
    types_impact: list | None = None
    maturite: str | None = None
    montant_recherche_amount: Decimal | None = None
    montant_recherche_currency: str | None = None
    duree_mois: int | None = None
    structure_financement_arr: list | None = None
    indicateurs_impact_json: Any = None
    localisation_pays_iso2: str | None = None
    localisation_ville: str | None = None
    statut: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FakeResult:
    def __init__(self, *, first_val=None, all_val=None, scalar_val=None):
        self._first = first_val
        self._all = all_val or []
        self._scalar = scalar_val

    def first(self):
        return self._first

    def all(self):
        return self._all

    def scalar_one(self):
        return self._scalar

    def scalar_one_or_none(self):
        return self._scalar


class FakeSession:
    """Routes execute() calls based on SQL substring to a queue of results."""
    def __init__(self):
        self.queries: list[tuple[str, dict]] = []
        self.responses: list[FakeResult] = []
        # nested savepoint
        class _NestedSP:
            def commit(self_):
                pass

            def rollback(self_):
                pass
        self._sp = _NestedSP()

    def queue(self, *results: FakeResult) -> None:
        self.responses.extend(results)

    def execute(self, sql, params=None):
        # Capture for assertions.
        sql_str = str(sql)
        self.queries.append((sql_str, dict(params or {})))
        upper = sql_str.upper()
        # INSERT INTO audit_log (record_audit) bypass the queue.
        if "AUDIT_LOG" in upper and "INSERT" in upper:
            return FakeResult()
        if self.responses:
            return self.responses.pop(0)
        return FakeResult()

    def flush(self):
        pass

    def begin_nested(self):
        return self._sp


def _make_pj_row(**kw):
    base = {
        "id": uuid4(),
        "account_id": uuid4(),
        "entreprise_id": uuid4(),
        "version": 1,
        "nom": "P",
        "description": None,
        "objectif_environnemental": None,
        "types_impact": None,
        "maturite": None,
        "montant_recherche_amount": None,
        "montant_recherche_currency": None,
        "duree_mois": None,
        "structure_financement_arr": None,
        "indicateurs_impact_json": None,
        "localisation_pays_iso2": None,
        "localisation_ville": None,
        "statut": "brouillon",
        "created_at": None,
        "updated_at": None,
    }
    base.update(kw)
    return FakeRow(**base)


def test_list_projets_with_filters():
    db = FakeSession()
    db.queue(
        FakeResult(scalar_val=2),
        FakeResult(all_val=[_make_pj_row(), _make_pj_row()]),
    )
    rows, total = srv.list_projets(
        db, account_id=uuid4(), statut="brouillon",
        type_impact="mitigation_carbone", page=1, limit=25,
    )
    assert total == 2
    assert len(rows) == 2


def test_list_projets_pagination_clamping():
    db = FakeSession()
    db.queue(FakeResult(scalar_val=0), FakeResult(all_val=[]))
    rows, total = srv.list_projets(
        db, account_id=uuid4(), page=0, limit=999,
    )
    assert total == 0
    # page=0 should be clamped to 1, limit=999 to 100.


def test_get_projet_not_found():
    db = FakeSession()
    db.queue(FakeResult(first_val=None))
    with pytest.raises(srv.ProjetNotFound):
        srv.get_projet(db, projet_id=uuid4(), account_id=uuid4())


def test_get_projet_ok():
    row = _make_pj_row(nom="X")
    db = FakeSession()
    db.queue(FakeResult(first_val=row))
    out = srv.get_projet(db, projet_id=row.id, account_id=row.account_id)
    assert out.nom == "X"


def test_create_projet_full_path():
    """create_projet runs:
    1) entreprise lookup, 2) INSERT, 3) audit insert (savepoint), 4) re-select.
    """
    db = FakeSession()
    eid = uuid4()
    aid = uuid4()
    uid = uuid4()
    pj_row = _make_pj_row(account_id=aid, entreprise_id=eid, nom="Eolien")
    db.queue(
        FakeResult(first_val=(eid,)),  # entreprise lookup
        FakeResult(),                  # INSERT projet
        FakeResult(first_val=pj_row),  # SELECT after insert
    )
    out = srv.create_projet(
        db, account_id=aid, user_id=uid,
        payload={
            "nom": "Eolien",
            "types_impact": ["mitigation_carbone"],
            "structure_financement_arr": ["subvention"],
            "indicateurs_impact_json": [{"key": "tCO2e", "value": 100, "unit": "t"}],
            "montant_recherche": {"amount": Decimal("1000"), "currency": "XOF"},
            "statut": "brouillon",
            "maturite": "pilote",
        },
    )
    assert out.nom == "Eolien"


def test_create_projet_missing_nom():
    db = FakeSession()
    with pytest.raises(ValueError):
        srv.create_projet(db, account_id=uuid4(), user_id=uuid4(), payload={})


def test_create_projet_no_entreprise():
    db = FakeSession()
    db.queue(FakeResult(first_val=None))
    with pytest.raises(RuntimeError):
        srv.create_projet(db, account_id=uuid4(), user_id=uuid4(), payload={"nom": "X"})


def test_patch_projet_no_change():
    aid = uuid4()
    pid = uuid4()
    eid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, entreprise_id=eid, nom="Same", version=1)
    db = FakeSession()
    db.queue(FakeResult(first_val=row))  # get_projet
    out = srv.patch_projet(
        db, projet_id=pid, account_id=aid, user_id=uuid4(),
        expected_version=1, payload={"nom": "Same"},
    )
    assert out.nom == "Same"


def test_patch_projet_version_conflict():
    aid = uuid4()
    pid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, version=2)
    db = FakeSession()
    db.queue(FakeResult(first_val=row))
    with pytest.raises(srv.VersionConflict):
        srv.patch_projet(
            db, projet_id=pid, account_id=aid, user_id=uuid4(),
            expected_version=1, payload={"nom": "Y"},
        )


def test_patch_projet_full_update():
    aid = uuid4()
    pid = uuid4()
    eid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, entreprise_id=eid, version=1, nom="Old")
    new_row = _make_pj_row(id=pid, account_id=aid, entreprise_id=eid, version=2, nom="New")
    db = FakeSession()
    db.queue(
        FakeResult(first_val=row),       # get_projet
        FakeResult(first_val=(2,)),      # UPDATE returning
        FakeResult(first_val=new_row),   # re-select
    )
    out = srv.patch_projet(
        db, projet_id=pid, account_id=aid, user_id=uuid4(),
        expected_version=1,
        payload={
            "nom": "New",
            "description": "d",
            "objectif_environnemental": "o",
            "types_impact": ["adaptation"],
            "maturite": "scale",
            "duree_mois": 6,
            "structure_financement_arr": ["equity"],
            "indicateurs_impact_json": [{"key": "k", "value": 1.0, "unit": "x"}],
            "localisation_pays_iso2": "SN",
            "localisation_ville": "Dakar",
            "statut": "en_recherche_financement",
            "montant_recherche": {"amount": Decimal("500"), "currency": "EUR"},
        },
    )
    assert out.nom == "New"
    assert out.version == 2


def test_patch_projet_set_money_to_none():
    aid = uuid4()
    pid = uuid4()
    row = _make_pj_row(
        id=pid, account_id=aid, version=1,
        montant_recherche_amount=Decimal("1"), montant_recherche_currency="XOF",
    )
    new_row = _make_pj_row(id=pid, account_id=aid, version=2)
    db = FakeSession()
    db.queue(
        FakeResult(first_val=row),
        FakeResult(first_val=(2,)),
        FakeResult(first_val=new_row),
    )
    out = srv.patch_projet(
        db, projet_id=pid, account_id=aid, user_id=uuid4(),
        expected_version=1, payload={"montant_recherche": None},
    )
    assert out.version == 2


def test_patch_projet_update_returning_none_then_not_found():
    aid = uuid4()
    pid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, version=1, nom="Old")
    db = FakeSession()
    db.queue(
        FakeResult(first_val=row),       # get_projet
        FakeResult(first_val=None),      # UPDATE returns nothing
        FakeResult(scalar_val=None),     # SELECT version returns nothing
    )
    with pytest.raises(srv.ProjetNotFound):
        srv.patch_projet(
            db, projet_id=pid, account_id=aid, user_id=uuid4(),
            expected_version=1, payload={"nom": "X"},
        )


def test_patch_projet_update_returning_none_then_version_conflict():
    aid = uuid4()
    pid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, version=1, nom="Old")
    db = FakeSession()
    db.queue(
        FakeResult(first_val=row),
        FakeResult(first_val=None),
        FakeResult(scalar_val=5),
    )
    with pytest.raises(srv.VersionConflict):
        srv.patch_projet(
            db, projet_id=pid, account_id=aid, user_id=uuid4(),
            expected_version=1, payload={"nom": "X"},
        )


def test_duplicate_projet():
    aid = uuid4()
    pid = uuid4()
    eid = uuid4()
    src_row = _make_pj_row(
        id=pid, account_id=aid, entreprise_id=eid, nom="Source",
        montant_recherche_amount=Decimal("1"), montant_recherche_currency="XOF",
    )
    new_row = _make_pj_row(
        id=uuid4(), account_id=aid, entreprise_id=eid, nom="Source (copie)", statut="brouillon",
    )
    db = FakeSession()
    db.queue(
        FakeResult(first_val=src_row),    # get_projet (initial)
        FakeResult(first_val=(eid,)),     # entreprise lookup (in create)
        FakeResult(),                     # INSERT projet
        FakeResult(first_val=new_row),    # re-select
    )
    out = srv.duplicate_projet(db, projet_id=pid, account_id=aid, user_id=uuid4())
    assert out.nom == "Source (copie)"
    assert out.statut == "brouillon"


def test_delete_projet_brouillon_ok():
    aid = uuid4()
    pid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, statut="brouillon")
    db = FakeSession()
    db.queue(
        FakeResult(first_val=row),  # get_projet
        FakeResult(),               # UPDATE deleted_at
    )
    srv.delete_projet(db, projet_id=pid, account_id=aid, user_id=uuid4(), confirm=False)


def test_delete_projet_finance_protected():
    aid = uuid4()
    pid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, statut="finance")
    db = FakeSession()
    db.queue(FakeResult(first_val=row))
    with pytest.raises(srv.DeleteProtected) as exc:
        srv.delete_projet(db, projet_id=pid, account_id=aid, user_id=uuid4(), confirm=False)
    assert exc.value.statut == "finance"


def test_delete_projet_finance_with_confirm():
    aid = uuid4()
    pid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, statut="en_execution")
    db = FakeSession()
    db.queue(
        FakeResult(first_val=row),
        FakeResult(),
    )
    srv.delete_projet(db, projet_id=pid, account_id=aid, user_id=uuid4(), confirm=True)


def test_transition_projet_invokes_patch():
    aid = uuid4()
    pid = uuid4()
    row = _make_pj_row(id=pid, account_id=aid, version=1, statut="brouillon")
    new_row = _make_pj_row(id=pid, account_id=aid, version=2, statut="en_recherche_financement")
    db = FakeSession()
    db.queue(
        FakeResult(first_val=row),
        FakeResult(first_val=(2,)),
        FakeResult(first_val=new_row),
    )
    out = srv.transition_projet(
        db, projet_id=pid, account_id=aid, user_id=uuid4(),
        expected_version=1, to="en_recherche_financement",
    )
    assert out.statut == "en_recherche_financement"
