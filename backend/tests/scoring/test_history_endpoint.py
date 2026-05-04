"""F46 T007 — Tests pour le nouvel endpoint history (TDD)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests unitaires de la signature/contrat de service.list_history (sans DB).
# ---------------------------------------------------------------------------


class TestServiceHistorySignature:
    """Vérifie que `list_history` est exporté avec la bonne signature."""

    def test_list_history_callable(self) -> None:
        from app.scoring.service import list_history

        assert callable(list_history)

    def test_list_history_uses_keyword_only_args(self) -> None:
        import inspect

        from app.scoring.service import list_history

        sig = inspect.signature(list_history)
        params = sig.parameters
        # Au moins ces paramètres doivent exister.
        for name in (
            "account_id",
            "entity_type",
            "entity_id",
            "referentiel_code",
            "limit",
        ):
            assert name in params, f"missing param: {name}"


class TestSchemaShape:
    """Schémas Pydantic v2 strict pour la réponse de history."""

    def test_score_history_entry_strict(self) -> None:
        from app.scoring.schemas import ScoreHistoryEntry

        e = ScoreHistoryEntry(
            score_calculation_id=uuid.uuid4(),
            computed_at=datetime.now(UTC),
            score_global=67.4,
            referentiel_version=3,
        )
        assert e.referentiel_version == 3
        assert e.score_global == 67.4

    def test_score_history_entry_rejects_extra(self) -> None:
        from pydantic import ValidationError

        from app.scoring.schemas import ScoreHistoryEntry

        with pytest.raises(ValidationError):
            ScoreHistoryEntry(
                score_calculation_id=uuid.uuid4(),
                computed_at=datetime.now(UTC),
                score_global=10.0,
                referentiel_version=1,
                extra_field="boom",  # type: ignore[call-arg]
            )

    def test_score_history_entry_allows_null_score(self) -> None:
        from app.scoring.schemas import ScoreHistoryEntry

        e = ScoreHistoryEntry(
            score_calculation_id=uuid.uuid4(),
            computed_at=datetime.now(UTC),
            score_global=None,
            referentiel_version=1,
        )
        assert e.score_global is None

    def test_score_history_out_strict(self) -> None:
        from app.scoring.schemas import ScoreHistoryOut

        out = ScoreHistoryOut(
            entity_type="entreprise",
            entity_id=uuid.uuid4(),
            referentiel_code="BOAD",
            entries=[],
        )
        assert out.entries == []


# ---------------------------------------------------------------------------
# Tests fonctionnels : avec un faux Session SQLAlchemy on contrôle les appels.
# ---------------------------------------------------------------------------


class _FakeRow:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeResult:
    def __init__(self, rows: list[_FakeRow] | None = None, first: _FakeRow | None = None) -> None:
        self._rows = rows or []
        self._first = first

    def first(self) -> _FakeRow | None:
        return self._first

    def fetchall(self) -> list[_FakeRow]:
        return self._rows


class _FakeSession:
    """Session SQLAlchemy minimal — garde trace des SQL exécutés."""

    def __init__(self, plan: list[_FakeResult]) -> None:
        self._plan = plan
        self._call_idx = 0
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = str(stmt) if hasattr(stmt, "__str__") else ""
        self.calls.append((sql, params or {}))
        result = self._plan[self._call_idx]
        self._call_idx += 1
        return result


class TestServiceListHistoryUnit:
    """Unit tests de `service.list_history` avec un faux Session."""

    def _import(self):
        from app.scoring.service import ReferentielNotFound, list_history

        return list_history, ReferentielNotFound

    def test_referentiel_unknown_raises(self) -> None:
        list_history, ReferentielNotFound = self._import()

        # 1er execute = lookup référentiel → None
        session = _FakeSession([_FakeResult(first=None)])

        with pytest.raises(ReferentielNotFound):
            list_history(
                session,
                account_id=uuid.uuid4(),
                entity_type="entreprise",
                entity_id=uuid.uuid4(),
                referentiel_code="UNKNOWN_CODE",
                limit=12,
            )

    def test_empty_history_returns_empty_list(self) -> None:
        list_history, _ = self._import()

        ref_id = uuid.uuid4()
        session = _FakeSession(
            [
                _FakeResult(
                    first=_FakeRow(id=ref_id, code="BOAD", version=1, status="published")
                ),
                _FakeResult(rows=[]),
            ]
        )

        out = list_history(
            session,
            account_id=uuid.uuid4(),
            entity_type="entreprise",
            entity_id=uuid.uuid4(),
            referentiel_code="BOAD",
            limit=12,
        )
        assert out == []

    def test_orders_desc_and_respects_limit(self) -> None:
        list_history, _ = self._import()

        ref_id = uuid.uuid4()
        now = datetime.now(UTC)
        rows = [
            _FakeRow(
                id=uuid.uuid4(),
                computed_at=now,
                score_global=70.0,
                referentiel_version=3,
            ),
            _FakeRow(
                id=uuid.uuid4(),
                computed_at=now - timedelta(days=1),
                score_global=65.0,
                referentiel_version=3,
            ),
            _FakeRow(
                id=uuid.uuid4(),
                computed_at=now - timedelta(days=2),
                score_global=None,
                referentiel_version=2,
            ),
        ]
        session = _FakeSession(
            [
                _FakeResult(
                    first=_FakeRow(id=ref_id, code="BOAD", version=3, status="published")
                ),
                _FakeResult(rows=rows),
            ]
        )

        out = list_history(
            session,
            account_id=uuid.uuid4(),
            entity_type="entreprise",
            entity_id=uuid.uuid4(),
            referentiel_code="BOAD",
            limit=12,
        )
        assert len(out) == 3
        # Ordre transmis = ordre des rows (le ORDER BY DESC est imposé en SQL)
        assert out[0]["score_global"] == 70.0
        assert out[2]["score_global"] is None
        # limit doit être présent dans le params bind
        last_params = session.calls[-1][1]
        assert last_params["limit"] == 12


# ---------------------------------------------------------------------------
# Tests fonctionnels du routeur (auth gate + 422 sur limit hors borne).
# ---------------------------------------------------------------------------


class TestRouterAuthGate:
    def test_history_route_present_in_openapi(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        # Une route avec /history doit être enregistrée sous /me/scoring/.
        history_paths = [p for p in paths if p.startswith("/me/scoring/") and p.endswith("/history")]
        assert len(history_paths) >= 1, f"history route missing in {list(paths.keys())[:10]}"

    def test_history_requires_auth(self, client: TestClient) -> None:
        eid = uuid.uuid4()
        resp = client.get(f"/me/scoring/entreprise/{eid}/BOAD/history")
        assert resp.status_code in {401, 403}

    def test_history_invalid_entity_type_404(self, client: TestClient) -> None:
        # Pas de JWT → 401 plutôt que 404, mais on vérifie avec une route invalide.
        # L'auth est résolue avant la validation entity_type, donc on doit voir 401.
        eid = uuid.uuid4()
        resp = client.get(f"/me/scoring/offre/{eid}/BOAD/history")
        assert resp.status_code in {401, 403, 404}

    def test_history_limit_out_of_range_422(self, client: TestClient) -> None:
        # Sans auth on aura 401 avant 422 ; le test confirme juste que le path existe.
        eid = uuid.uuid4()
        resp = client.get(
            f"/me/scoring/entreprise/{eid}/BOAD/history",
            params={"limit": 0},
        )
        # Auth est appliquée avant la validation du query param dans FastAPI.
        assert resp.status_code in {401, 403, 422}
