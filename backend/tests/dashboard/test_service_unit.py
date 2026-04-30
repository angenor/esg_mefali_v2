"""F32 — Tests unitaires des helpers et de build_summary/build_export.

Utilise des sessions mockees pour atteindre la couverture sans DB reelle.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.dashboard import service as svc


class _FakeMapping:
    def __init__(self, d: dict[str, Any]) -> None:
        self._d = d

    def __getitem__(self, key: str) -> Any:
        return self._d[key]

    def __iter__(self):
        return iter(self._d)

    def __len__(self) -> int:
        return len(self._d)

    def keys(self):
        return self._d.keys()

    def items(self):
        return self._d.items()

    def values(self):
        return self._d.values()


class _FakeRow:
    """Mimics SQLAlchemy Row's ``_mapping`` interface."""

    def __init__(self, d: dict[str, Any]) -> None:
        self._mapping = _FakeMapping(d)


# ---------------------------------------------------------------------------
# _serialize_value
# ---------------------------------------------------------------------------


class TestSerializeValue:
    def test_none(self) -> None:
        assert svc._serialize_value(None) is None

    def test_uuid(self) -> None:
        u = uuid.uuid4()
        assert svc._serialize_value(u) == str(u)

    def test_decimal(self) -> None:
        assert svc._serialize_value(Decimal("1.25")) == 1.25

    def test_datetime(self) -> None:
        d = datetime(2026, 4, 30, tzinfo=UTC)
        out = svc._serialize_value(d)
        assert isinstance(out, str) and "2026-04-30" in out

    def test_date(self) -> None:
        out = svc._serialize_value(date(2026, 4, 30))
        assert out == "2026-04-30"

    def test_list_recursion(self) -> None:
        u = uuid.uuid4()
        out = svc._serialize_value([u, Decimal("3.0"), None])
        assert out == [str(u), 3.0, None]

    def test_dict_recursion(self) -> None:
        u = uuid.uuid4()
        out = svc._serialize_value({"id": u, "n": Decimal("1.5")})
        assert out == {"id": str(u), "n": 1.5}

    def test_passthrough(self) -> None:
        assert svc._serialize_value("hello") == "hello"
        assert svc._serialize_value(42) == 42
        assert svc._serialize_value(True) is True


class TestRowToDict:
    def test_none(self) -> None:
        assert svc._row_to_dict(None) == {}

    def test_with_mapping(self) -> None:
        u = uuid.uuid4()
        row = _FakeRow({"id": u, "name": "Foo", "amount": Decimal("9.99")})
        out = svc._row_to_dict(row)
        assert out == {"id": str(u), "name": "Foo", "amount": 9.99}


# ---------------------------------------------------------------------------
# build_summary / build_export with mocked Session
# ---------------------------------------------------------------------------


def _empty_session() -> MagicMock:
    """Return a Session mock where every execute() returns empty results."""
    sess = MagicMock()

    def _exec(*_args, **_kwargs):
        result = MagicMock()
        result.all.return_value = []
        result.first.return_value = None
        result.scalar.return_value = 0
        return result

    sess.execute.side_effect = _exec
    return sess


def test_build_summary_empty_account() -> None:
    aid = uuid.uuid4()
    out = svc.build_summary(_empty_session(), aid)
    assert out.account_id == aid
    assert out.scores == []
    assert out.carbon == []
    assert out.credit_score is None
    assert out.candidatures.total == 0
    assert out.candidatures.recent == []
    assert out.rapports.total == 0
    assert out.attestations.active == 0
    assert out.attestations.revoked == 0
    assert out.next_actions == []


def test_build_export_empty_account() -> None:
    aid = uuid.uuid4()
    out = svc.build_export(_empty_session(), aid)
    assert out.account == {"id": str(aid)}
    assert out.entreprise is None
    assert out.projets == []
    assert out.candidatures == []
    assert out.scores == []
    assert out.carbon == []
    assert out.credit_score is None
    assert out.rapports == []
    assert out.attestations == []
    assert out.consents == []
    assert out.action_plan == []


# ---------------------------------------------------------------------------
# Populated session via per-call return values
# ---------------------------------------------------------------------------


@pytest.fixture()
def populated_session() -> MagicMock:
    """Returns a Session where successive execute() calls feed each block."""
    score_row = _FakeRow(
        {
            "referentiel_code": "ESG_MEFALI",
            "referentiel_version": 1,
            "score_global": Decimal("80.0"),
            "coverage_ratio": Decimal("0.9"),
            "computed_at": datetime(2026, 4, 1, tzinfo=UTC),
        }
    )
    carbon_row = _FakeRow(
        {
            "year": 2025,
            "total_tco2e": Decimal("100.0"),
            "computed_at": datetime(2026, 4, 1, tzinfo=UTC),
        }
    )
    credit_row = _FakeRow(
        {
            "solvabilite": 70,
            "impact_vert": 80,
            "combine": 75,
            "methodologie_version": 1,
            "coherence_warning": False,
            "computed_at": datetime(2026, 4, 1, tzinfo=UTC),
        }
    )
    counters_row = _FakeRow({"statut": "brouillon", "n": 2})
    candidature_row = _FakeRow(
        {
            "id": uuid.uuid4(),
            "projet_id": uuid.uuid4(),
            "offre_id": uuid.uuid4(),
            "statut": "brouillon",
            "soumission_at": None,
            "created_at": datetime(2026, 4, 1, tzinfo=UTC),
        }
    )
    rapport_row = _FakeRow(
        {
            "id": uuid.uuid4(),
            "entity_type": "entreprise",
            "entity_id": uuid.uuid4(),
            "referentiels": ["ESG_MEFALI"],
            "language": "fr",
            "generated_at": datetime(2026, 4, 1, tzinfo=UTC),
        }
    )
    att_counters = _FakeRow({"active": 1, "revoked": 0})
    att_row = _FakeRow(
        {
            "id": uuid.uuid4(),
            "public_id": uuid.uuid4(),
            "generated_at": datetime(2026, 4, 1, tzinfo=UTC),
            "valid_until": datetime(2027, 4, 1, tzinfo=UTC),
            "revoked_at": None,
        }
    )
    action_row = _FakeRow(
        {
            "id": uuid.uuid4(),
            "title": "Bilan carbone",
            "category": "carbone",
            "priority": "haute",
            "status": "todo",
            "horizon_at": date(2026, 12, 31),
        }
    )

    queue: list[MagicMock] = []

    def _add_all(rows: list[Any]) -> None:
        m = MagicMock()
        m.all.return_value = rows
        m.first.return_value = rows[0] if rows else None
        m.scalar.return_value = len(rows)
        queue.append(m)

    def _add_first(row: Any) -> None:
        m = MagicMock()
        m.first.return_value = row
        m.all.return_value = [row] if row is not None else []
        m.scalar.return_value = 1 if row is not None else 0
        queue.append(m)

    def _add_scalar(v: int) -> None:
        m = MagicMock()
        m.scalar.return_value = v
        m.all.return_value = []
        m.first.return_value = None
        queue.append(m)

    # Order matches build_summary internal call sequence.
    _add_all([score_row])
    _add_all([carbon_row])
    _add_first(credit_row)
    _add_all([counters_row])
    _add_all([candidature_row])
    _add_scalar(1)
    _add_all([rapport_row])
    _add_first(att_counters)
    _add_all([att_row])
    _add_all([action_row])

    sess = MagicMock()
    sess.execute.side_effect = queue
    return sess


def test_build_summary_populated(populated_session) -> None:
    aid = uuid.uuid4()
    out = svc.build_summary(populated_session, aid)

    assert len(out.scores) == 1
    assert out.scores[0].referentiel_code == "ESG_MEFALI"
    assert len(out.carbon) == 1
    assert out.credit_score is not None
    assert out.credit_score.combine == 75
    assert out.candidatures.counters_by_statut == {"brouillon": 2}
    assert out.candidatures.total == 2
    assert len(out.candidatures.recent) == 1
    assert out.rapports.total == 1
    assert len(out.rapports.recent) == 1
    assert out.attestations.active == 1
    assert out.attestations.revoked == 0
    assert len(out.attestations.recent) == 1
    assert len(out.next_actions) == 1
    assert out.next_actions[0].priority == "haute"
