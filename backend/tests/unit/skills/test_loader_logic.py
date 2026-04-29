"""Tests F19 — logique du loader testée via stubs (sans DB).

Le test DB-réel est gated dans ``tests/integration``. Ici on couvre les chemins
de sélection/priorité avec une session mockée.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any
from unittest.mock import MagicMock

from app.skills.loader import _all_sources_verified, load_active_skills


class _SkillRec:
    def __init__(
        self,
        *,
        name: str,
        domain: str,
        rules: dict[str, Any],
        status: str = "published",
    ) -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.domain = domain
        self.activation_rules = rules
        self.status = status
        self.version = 1
        self.tool_whitelist = ["ask_qcu"]
        self.prompt_expert = "expert"
        self.procedure = ""


def _wrap_session(rows: list) -> Any:
    """Session mock retournant ``rows`` pour la requête sources."""
    session = MagicMock()
    result = MagicMock()
    result.all.return_value = rows
    session.execute.return_value = result
    return session


def test_all_sources_verified_empty_returns_true() -> None:
    session = _wrap_session([])
    ok, max_d = _all_sources_verified(session, uuid.uuid4())
    assert ok is True
    assert max_d is None


def test_all_sources_verified_all_ok_returns_max_date() -> None:
    rows = [("verified", date(2025, 1, 1)), ("verified", date(2026, 5, 1))]
    session = _wrap_session(rows)
    ok, max_d = _all_sources_verified(session, uuid.uuid4())
    assert ok is True
    assert max_d == date(2026, 5, 1)


def test_all_sources_verified_one_pending_returns_false() -> None:
    rows = [("verified", date(2025, 1, 1)), ("pending", None)]
    session = _wrap_session(rows)
    ok, _ = _all_sources_verified(session, uuid.uuid4())
    assert ok is False


def _make_loader_session(skills: list[_SkillRec], source_rows: list) -> Any:
    """Mock ``session.execute`` qui distingue list-skills vs sources-verify."""
    session = MagicMock()

    def execute(stmt: Any) -> Any:  # noqa: ANN401
        compiled = str(stmt).lower()
        result = MagicMock()
        if "verification_status" in compiled or "skill_source" in compiled:
            result.all.return_value = source_rows
            return result
        result.scalars.return_value = [s for s in skills if s.status == "published"]
        return result

    session.execute = execute
    return session


def test_load_active_skills_priority_truncates_to_two() -> None:
    s_dossier = _SkillRec(name="dossier_gcf", domain="dossier", rules={"any_of": [{"page": "/p"}]})
    s_scoring = _SkillRec(name="scoring", domain="scoring", rules={"any_of": [{"page": "/p"}]})
    s_diag = _SkillRec(name="diag", domain="diagnostic", rules={"any_of": [{"page": "/p"}]})

    session = _make_loader_session(
        [s_diag, s_dossier, s_scoring],
        [("verified", date(2026, 1, 1))],
    )
    out = load_active_skills({"page": "/p"}, session)
    assert len(out) == 2
    assert out[0].domain == "dossier"
    assert out[1].domain == "scoring"


def test_load_active_skills_excludes_non_matching_context() -> None:
    s = _SkillRec(name="x", domain="diagnostic", rules={"any_of": [{"page": "/profil/projets/*"}]})
    session = _make_loader_session([s], [])
    out = load_active_skills({"page": "/autre"}, session)
    assert out == []


def test_load_active_skills_excludes_skills_with_unverified_source() -> None:
    s = _SkillRec(name="x", domain="diagnostic", rules={"any_of": [{"page": "/p"}]})
    session = _make_loader_session([s], [("pending", None)])
    out = load_active_skills({"page": "/p"}, session)
    assert out == []


def test_load_active_skills_filters_drafts() -> None:
    s_pub = _SkillRec(name="pub", domain="diagnostic", rules={"any_of": [{"page": "/p"}]})
    s_draft = _SkillRec(
        name="draft", domain="dossier", rules={"any_of": [{"page": "/p"}]},
        status="draft",
    )
    session = _make_loader_session(
        [s_pub, s_draft], [("verified", date(2026, 1, 1))]
    )
    out = load_active_skills({"page": "/p"}, session)
    assert [s.name for s in out] == ["pub"]
