"""F17 US2 + US4 — Tests ``delete_project`` (destructif)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from app.audit.schemas import SourceOfChange
from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.mutations import delete_project as mod
from app.orchestrator.tools.mutations._rate_limit import reset_rate_limit_state


@pytest.fixture(autouse=True)
def _setup() -> None:
    reset_rate_limit_state()
    mod.register()
    yield
    reset_rate_limit_state()


def test_register_adds_tool() -> None:
    assert "delete_project" in TOOL_REGISTRY


def test_blocks_without_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-002 — `delete_project` sans confirmation est rejeté."""

    def fake_delete(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("delete_projet ne doit pas être appelé")

    monkeypatch.setattr(mod, "delete_projet", fake_delete)

    pid = uuid4()
    payload = mod.DeleteProjectPayload(projet_id=pid)  # confirmed=False par défaut
    result = mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id="acc-1",
        user_id="u-1",
        payload=payload,
    )

    assert isinstance(result, dict)
    assert result.get("requires_confirmation") is True
    assert result.get("tool") == "delete_project"


def test_executes_with_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_delete(db: Any, **kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(mod, "delete_projet", fake_delete)

    pid = uuid4()
    payload = mod.DeleteProjectPayload(projet_id=pid, confirmed=True)
    result = mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id="acc-1",
        user_id="u-1",
        payload=payload,
    )

    assert result == {"deleted": True, "projet_id": str(pid)}
    assert captured["projet_id"] == pid
    assert captured["source_of_change"] == SourceOfChange.LLM
    assert captured["confirm"] is True
