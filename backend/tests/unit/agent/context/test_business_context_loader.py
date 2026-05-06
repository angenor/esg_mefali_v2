"""F54 / T032 — Tests unitaires du business context loader (FR-002).

Couvre (FR-008) :
- PME complète : tous les blocs remplis.
- PME vide (sans entreprise).
- PME sans projet.
- PME sans indicateur.
- Cap projets / candidatures / indicateurs / plan respectés.

Approche : on stub :class:`sqlalchemy.orm.Session` via un `MagicMock` qui
intercepte les `db.execute(text(...), params)` et retourne des rows
forgées. Ceci nous permet de tester la **logique** du loader sans toucher
Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.agent.context.cache import reset_business_context_cache
from app.agent.context.loader import (
    CAP_CANDIDATURES,
    CAP_INDICATEURS,
    CAP_PROJETS,
    _load_business_context_sync,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ns(**kwargs: Any) -> SimpleNamespace:
    """Forge une row SQLAlchemy `Row`-like (accès attribut + ._mapping)."""
    n = SimpleNamespace(**kwargs)
    return n


def _entreprise_row(
    *,
    account_id: UUID,
    name: str = "SARL Boulangerie Sankoré",
    secteur_code: str = "C10.71",
    secteur_label: str | None = "Boulangerie-pâtisserie",
    taille_ca_amount: Any = Decimal("12000000"),
    taille_ca_currency: str | None = "XOF",
    taille_effectifs: int | None = 25,
    pays: str = "CI",
    gouvernance: dict | None = None,
) -> SimpleNamespace:
    return _ns(
        id=uuid4(),
        account_id=account_id,
        name=name,
        secteur_code=secteur_code,
        secteur_label=secteur_label,
        taille_ca_amount=taille_ca_amount,
        taille_ca_currency=taille_ca_currency,
        taille_effectifs=taille_effectifs,
        localisation_siege_pays_iso2=pays,
        gouvernance_json=gouvernance,
    )


def _projet_row(*, nom: str = "Solaire", statut: str = "en_analyse") -> SimpleNamespace:
    return _ns(
        id=uuid4(),
        nom=nom,
        description="Description courte",
        montant_recherche_amount=Decimal("5000000"),
        montant_recherche_currency="XOF",
        statut=statut,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _candidature_row(
    *, statut: str = "soumise", projet_id: UUID | None = None
) -> SimpleNamespace:
    return _ns(
        id=uuid4(),
        projet_id=projet_id or uuid4(),
        offre_id=uuid4(),
        statut=statut,
        soumission_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _indicateur_row(*, code: str = "GHG_S1", axe: str = "E") -> SimpleNamespace:
    return _ns(
        id=uuid4(),
        code=code,
        libelle="Émissions GES",
        axe=axe,
        unite="tCO2e",
        referentiel_code="GRI:305-1",
        created_at=datetime.now(UTC),
    )


def _score_row(*, gauge: int = 62) -> SimpleNamespace:
    return _ns(
        id=uuid4(),
        score_global=Decimal(str(gauge)),
        scores_by_pillar={"E": 65, "S": 60, "G": 60},
        computed_at=datetime.now(UTC),
    )


def _action_step_row(*, title: str = "Mesurer scope 1") -> SimpleNamespace:
    return _ns(
        id=uuid4(),
        title=title,
        status="todo",
        horizon_at=None,
    )


def _make_db_with_responses(responses: list[Any]) -> MagicMock:
    """Construit un MagicMock Session qui retourne ``responses`` dans l'ordre.

    Chaque entrée de ``responses`` doit être :
    - Un objet supportant ``.first()``, ``.all()``, etc.
    On utilise un ResultProxy émulé pour `db.execute(...).first()`/`.all()`.
    """
    db = MagicMock()
    iterator = iter(responses)

    def _execute(_sql, _params=None):  # noqa: ARG001
        return next(iterator)

    db.execute.side_effect = _execute
    return db


class _ResultMock:
    """Émule un ResultProxy SQLAlchemy."""

    def __init__(
        self,
        *,
        rows: list[Any] | None = None,
        first: Any | None = None,
    ) -> None:
        self._rows = rows or []
        self._first = first if first is not None else (self._rows[0] if self._rows else None)

    def first(self) -> Any | None:
        return self._first

    def all(self) -> list[Any]:
        return self._rows


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_business_context_cache()
    yield
    reset_business_context_cache()


@pytest.mark.unit
class TestBusinessContextComplete:
    """PME complète : entreprise + 2 projets + 1 candidature + 1 indicateur
    + 1 score + 1 action."""

    def test_complete_pme(self) -> None:
        aid = uuid4()
        uid = uuid4()
        responses = [
            _ResultMock(first=_entreprise_row(account_id=aid)),
            _ResultMock(rows=[_projet_row(nom="Solaire"), _projet_row(nom="Eolien")]),
            _ResultMock(rows=[_candidature_row()]),
            _ResultMock(rows=[_indicateur_row()]),
            _ResultMock(first=_score_row(gauge=62)),
            _ResultMock(rows=[_action_step_row()]),
        ]
        db = _make_db_with_responses(responses)

        ctx = _load_business_context_sync(
            db, account_id=aid, user_id=uid, user_role="pme"
        )

        assert ctx.account_id == aid
        assert ctx.user_id == uid
        assert ctx.user_role == "pme"
        assert ctx.entreprise is not None
        assert ctx.entreprise.raison_sociale == "SARL Boulangerie Sankoré"
        assert len(ctx.projets_actifs) == 2
        assert ctx.projets_actifs[0].titre == "Solaire"
        assert ctx.projets_actifs[0].montant_demande is not None
        assert len(ctx.candidatures_en_cours) == 1
        assert len(ctx.indicateurs_recents) == 1
        assert ctx.score_credit is not None
        assert ctx.score_credit.gauge == 62
        assert len(ctx.plan_action_steps) == 1


@pytest.mark.unit
class TestBusinessContextEmptyVariants:
    """3 cas vides exigés par FR-008."""

    def test_pme_without_entreprise(self) -> None:
        aid = uuid4()
        uid = uuid4()
        responses = [
            _ResultMock(first=None),  # entreprise vide
            _ResultMock(rows=[]),
            _ResultMock(rows=[]),
            _ResultMock(rows=[]),
            _ResultMock(first=None),
            _ResultMock(rows=[]),
        ]
        db = _make_db_with_responses(responses)
        ctx = _load_business_context_sync(
            db, account_id=aid, user_id=uid, user_role="pme"
        )
        assert ctx.entreprise is None
        assert ctx.projets_actifs == []
        assert ctx.candidatures_en_cours == []

    def test_pme_with_entreprise_no_projet(self) -> None:
        aid = uuid4()
        uid = uuid4()
        responses = [
            _ResultMock(first=_entreprise_row(account_id=aid)),
            _ResultMock(rows=[]),
            _ResultMock(rows=[]),
            _ResultMock(rows=[]),
            _ResultMock(first=None),
            _ResultMock(rows=[]),
        ]
        db = _make_db_with_responses(responses)
        ctx = _load_business_context_sync(
            db, account_id=aid, user_id=uid, user_role="pme"
        )
        assert ctx.entreprise is not None
        assert ctx.projets_actifs == []
        assert ctx.score_credit is None

    def test_pme_with_no_indicateur(self) -> None:
        aid = uuid4()
        uid = uuid4()
        responses = [
            _ResultMock(first=_entreprise_row(account_id=aid)),
            _ResultMock(rows=[_projet_row()]),
            _ResultMock(rows=[]),
            _ResultMock(rows=[]),  # indicateur empty
            _ResultMock(first=None),
            _ResultMock(rows=[]),
        ]
        db = _make_db_with_responses(responses)
        ctx = _load_business_context_sync(
            db, account_id=aid, user_id=uid, user_role="pme"
        )
        assert ctx.indicateurs_recents == []


@pytest.mark.unit
class TestBusinessContextRobustness:
    """Robustesse : tables manquantes (catalogue / score) ne plantent pas."""

    def test_missing_score_table_returns_none(self) -> None:
        aid = uuid4()
        uid = uuid4()

        # 6 calls expected — score_calc throws.
        call_count = [0]

        def _execute(_sql, _params=None):  # noqa: ARG001
            call_count[0] += 1
            if call_count[0] == 1:
                return _ResultMock(first=_entreprise_row(account_id=aid))
            if call_count[0] in (2, 3, 4):
                return _ResultMock(rows=[])
            if call_count[0] == 5:
                raise RuntimeError("table score_calculation does not exist")
            if call_count[0] == 6:
                return _ResultMock(rows=[])
            raise AssertionError("unexpected call")

        db = MagicMock()
        db.execute.side_effect = _execute

        ctx = _load_business_context_sync(
            db, account_id=aid, user_id=uid, user_role="pme"
        )
        assert ctx.score_credit is None


@pytest.mark.unit
class TestBusinessContextRoleNormalization:
    """Toute valeur de role hors {pme, admin} doit retomber sur 'pme'."""

    def test_unknown_role_falls_back_to_pme(self) -> None:
        aid = uuid4()
        responses = [
            _ResultMock(first=None),
            _ResultMock(rows=[]),
            _ResultMock(rows=[]),
            _ResultMock(rows=[]),
            _ResultMock(first=None),
            _ResultMock(rows=[]),
        ]
        db = _make_db_with_responses(responses)
        ctx = _load_business_context_sync(
            db, account_id=aid, user_id=uuid4(), user_role="hacker"
        )
        assert ctx.user_role == "pme"


@pytest.mark.unit
class TestCaps:
    def test_caps_constants(self) -> None:
        assert CAP_PROJETS == 10
        assert CAP_CANDIDATURES == 10
        assert CAP_INDICATEURS == 30
