"""F58 / T034 — Tests unitaires tool_status (FR-007, FR-008, FR-009)."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.agent.guardrails.tool_status import (
    _CACHE_TTL_S,
    _reset_cache,
    cache_invalidate,
    get_disabled_tools,
)


@pytest.fixture(autouse=True)
def _reset() -> None:
    _reset_cache()
    yield
    _reset_cache()


def _make_session_with_disabled(names: list[str]) -> MagicMock:
    """Crée une session SQLAlchemy mock retournant ``names`` désactivés."""
    sess = MagicMock()
    rows = [{"tool_name": n} for n in names]
    mappings_obj = MagicMock()
    mappings_obj.all.return_value = rows
    exec_result = MagicMock()
    exec_result.mappings.return_value = mappings_obj
    sess.execute.return_value = exec_result
    return sess


@pytest.mark.unit
def test_get_disabled_tools_empty() -> None:
    sess = _make_session_with_disabled([])
    disabled = get_disabled_tools(sess)
    assert disabled == set()


@pytest.mark.unit
def test_get_disabled_tools_returns_set() -> None:
    sess = _make_session_with_disabled(["create_project", "generate_dossier"])
    disabled = get_disabled_tools(sess)
    assert disabled == {"create_project", "generate_dossier"}


@pytest.mark.unit
def test_cache_TTL_smoke() -> None:
    """Le cache dans la fenêtre TTL ne re-query pas la DB."""
    sess = _make_session_with_disabled(["x"])
    _ = get_disabled_tools(sess)
    _ = get_disabled_tools(sess)
    # Deux appels mais une seule exécution SQL
    assert sess.execute.call_count == 1


@pytest.mark.unit
def test_cache_invalidate_forces_requery() -> None:
    sess = _make_session_with_disabled(["a"])
    _ = get_disabled_tools(sess)
    cache_invalidate()
    _ = get_disabled_tools(sess)
    assert sess.execute.call_count == 2


@pytest.mark.unit
def test_cache_ttl_constant_30s() -> None:
    """Cache TTL doit être ≤ 30s pour respecter SC-004 (réaction < 1 min)."""
    assert _CACHE_TTL_S <= 30.0


@pytest.mark.unit
def test_get_disabled_tools_handles_db_error_safely() -> None:
    """Si la DB échoue, retourne set vide (pas de blocage du flux agent)."""
    sess = MagicMock()
    sess.execute.side_effect = Exception("DB down")
    disabled = get_disabled_tools(sess)
    assert disabled == set()


@pytest.mark.unit
def test_disable_tool_inserts_or_updates() -> None:
    """``disable_tool`` exécute INSERT ON CONFLICT UPDATE et invalide le cache."""
    from app.agent.guardrails.tool_status import disable_tool

    sess = MagicMock()
    admin_id = uuid4()
    disable_tool(sess, "create_project", admin_user_id=admin_id, reason="test")
    # Au moins 1 execute pour l'upsert (peut y avoir audit log en plus, mais on tolère)
    assert sess.execute.call_count >= 1


@pytest.mark.unit
def test_enable_tool_updates() -> None:
    from app.agent.guardrails.tool_status import enable_tool

    sess = MagicMock()
    admin_id = uuid4()
    enable_tool(sess, "create_project", admin_user_id=admin_id)
    assert sess.execute.call_count >= 1
