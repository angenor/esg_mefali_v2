"""F17 US2 — Tests ``update_project``."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.audit.schemas import SourceOfChange
from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.mutations import update_project as mod
from app.orchestrator.tools.mutations._rate_limit import reset_rate_limit_state


@pytest.fixture(autouse=True)
def _setup() -> None:
    reset_rate_limit_state()
    mod.register()
    yield
    reset_rate_limit_state()


def test_register_adds_tool() -> None:
    assert "update_project" in TOOL_REGISTRY


def test_projet_id_required() -> None:
    with pytest.raises(ValidationError):
        mod.UpdateProjectPayload(  # type: ignore[call-arg]
            expected_version=1, fields={"nom": "x"}
        )


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        mod.UpdateProjectPayload(
            projet_id=uuid4(),
            expected_version=1,
            fields={"nom": "x", "rogue": "y"},  # type: ignore[arg-type]
        )


def test_handle_no_fields_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_patch(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("ne doit pas être appelé")

    monkeypatch.setattr(mod, "patch_projet", fake_patch)

    payload = mod.UpdateProjectPayload(
        projet_id=uuid4(), expected_version=1, fields={}
    )
    result = mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id=uuid4(),
        user_id=uuid4(),
        payload=payload,
    )
    assert result == {"updated": False, "reason": "no_fields_provided"}


def test_handle_calls_patch_with_llm_source(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    pid = uuid4()

    class _Row:
        id = pid
        version = 2

    def fake_patch(db: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return _Row()

    monkeypatch.setattr(mod, "patch_projet", fake_patch)

    payload = mod.UpdateProjectPayload(
        projet_id=pid, expected_version=1, fields={"nom": "Nouveau nom"}
    )
    result = mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id="acc-1",
        user_id="u-1",
        payload=payload,
    )

    assert result["updated"] is True
    assert result["version"] == 2
    assert "nom" in result["fields_changed"]
    assert captured["source_of_change"] == SourceOfChange.LLM
    assert captured["expected_version"] == 1
    assert captured["projet_id"] == pid
