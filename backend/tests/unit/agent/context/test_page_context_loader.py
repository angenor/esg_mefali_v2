"""F54 / T042 — Tests unitaires page context loader (US3).

Couvre (FR-008) :
- Projet (charge entité + candidatures liées).
- Candidature (charge entité + offre).
- Indicateur (charge entité catalogue).
- Scoring (charge le scoring le plus récent).
- entity_type=None → contexte minimal cohérent (data={}).
- Cross-tenant : entité d'un autre account → data vide (RLS-like).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.agent.context.loader import _load_page_context_sync


def _ns(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


class _Result:
    def __init__(self, *, rows=None, first=None) -> None:
        self._rows = rows or []
        self._first = first if first is not None else (
            self._rows[0] if self._rows else None
        )

    def first(self) -> Any | None:
        return self._first

    def all(self) -> list[Any]:
        return self._rows


def _make_db(responses: list[Any]) -> MagicMock:
    db = MagicMock()
    iterator = iter(responses)

    def _execute(_sql, _params=None):  # noqa: ARG001
        return next(iterator)

    db.execute.side_effect = _execute
    return db


@pytest.mark.unit
class TestPageContextProjet:
    def test_projet_loads_with_candidatures(self) -> None:
        aid = uuid4()
        pid = uuid4()
        projet_row = _ns(
            id=pid,
            nom="Solaire",
            description="Description",
            statut="en_analyse",
            montant_recherche_amount=Decimal("5000000"),
            montant_recherche_currency="XOF",
        )
        cand_rows = [
            _ns(id=uuid4(), offre_id=uuid4(), statut="soumise"),
        ]
        db = _make_db([
            _Result(first=projet_row),
            _Result(rows=cand_rows),
        ])
        ctx = _load_page_context_sync(
            db,
            page_ctx_dict={"page_route": "/projet/abc", "entity_type": "Projet", "entity_id": str(pid)},
            account_id=aid,
        )
        assert ctx.entity_type == "Projet"
        assert ctx.entity_id == pid
        assert ctx.data["projet"]["titre"] == "Solaire"
        assert len(ctx.related) == 1
        assert ctx.related[0]["type"] == "candidature"

    def test_projet_not_found_returns_empty_data(self) -> None:
        aid = uuid4()
        pid = uuid4()
        db = _make_db([
            _Result(first=None),  # projet introuvable (cross-tenant ou inexistant)
        ])
        ctx = _load_page_context_sync(
            db,
            page_ctx_dict={"page_route": "/projet/abc", "entity_type": "Projet", "entity_id": str(pid)},
            account_id=aid,
        )
        assert ctx.entity_type == "Projet"
        # Pas de data — RLS 404 silencieux (P2).
        assert ctx.data == {}


@pytest.mark.unit
class TestPageContextCandidature:
    def test_candidature_loads(self) -> None:
        aid = uuid4()
        cid = uuid4()
        cand_row = _ns(
            id=cid,
            projet_id=uuid4(),
            offre_id=uuid4(),
            statut="soumise",
            snapshot_json={"step": 3},
        )
        db = _make_db([_Result(first=cand_row)])
        ctx = _load_page_context_sync(
            db,
            page_ctx_dict={"page_route": "/candidature", "entity_type": "Candidature", "entity_id": str(cid)},
            account_id=aid,
        )
        assert ctx.entity_type == "Candidature"
        assert ctx.data["candidature"]["statut"] == "soumise"
        assert ctx.data["candidature"]["has_snapshot"] is True


@pytest.mark.unit
class TestPageContextIndicateur:
    def test_indicateur_loads(self) -> None:
        aid = uuid4()
        iid = uuid4()
        row = _ns(
            id=iid,
            code="GHG_S1",
            libelle="Émissions GES",
            axe="E",
            unite="tCO2e",
            referentiel_code="GRI:305-1",
        )
        db = _make_db([_Result(first=row)])
        ctx = _load_page_context_sync(
            db,
            page_ctx_dict={"page_route": "/indicateur", "entity_type": "Indicateur", "entity_id": str(iid)},
            account_id=aid,
        )
        assert ctx.entity_type == "Indicateur"
        assert ctx.data["indicateur"]["code"] == "GHG_S1"
        assert ctx.data["indicateur"]["axe"] == "E"


@pytest.mark.unit
class TestPageContextScoring:
    def test_scoring_loads_latest(self) -> None:
        aid = uuid4()
        score_row = _ns(
            id=uuid4(),
            score_global=Decimal("65"),
            scores_by_pillar={"E": 70, "S": 60, "G": 65},
            computed_at=datetime.now(UTC),
        )
        db = _make_db([_Result(first=score_row)])
        ctx = _load_page_context_sync(
            db,
            page_ctx_dict={"page_route": "/scoring", "entity_type": "Scoring"},
            account_id=aid,
        )
        assert ctx.entity_type == "Scoring"
        assert "scoring" in ctx.data
        assert ctx.data["scoring"]["gauge"] == 65


@pytest.mark.unit
class TestPageContextNoEntity:
    def test_none_entity_minimal(self) -> None:
        aid = uuid4()
        db = MagicMock()  # rien n'est exécuté en DB.
        ctx = _load_page_context_sync(
            db,
            page_ctx_dict={"page_route": "/", "entity_type": None},
            account_id=aid,
        )
        assert ctx.entity_type is None
        assert ctx.entity_id is None
        assert ctx.data == {}
        assert ctx.related == []
        # Aucune requête DB déclenchée.
        db.execute.assert_not_called()

    def test_unknown_entity_type_falls_back(self) -> None:
        aid = uuid4()
        db = MagicMock()
        ctx = _load_page_context_sync(
            db,
            page_ctx_dict={"page_route": "/x", "entity_type": "UnknownThing"},
            account_id=aid,
        )
        assert ctx.entity_type is None
        assert ctx.data == {}

    def test_invalid_entity_id_drops_silently(self) -> None:
        aid = uuid4()
        db = MagicMock()
        ctx = _load_page_context_sync(
            db,
            page_ctx_dict={"page_route": "/p", "entity_type": "Projet", "entity_id": "not-a-uuid"},
            account_id=aid,
        )
        # entity_id devient None → on ne déclenche pas le sub-loader.
        assert ctx.entity_id is None
        assert ctx.data == {}
        db.execute.assert_not_called()
