"""F17 US2 — Tests ``create_project``."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.audit.schemas import SourceOfChange
from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.mutations import create_project as mod
from app.orchestrator.tools.mutations._rate_limit import reset_rate_limit_state


@pytest.fixture(autouse=True)
def _setup() -> None:
    reset_rate_limit_state()
    mod.register()
    yield
    reset_rate_limit_state()


def test_register_adds_tool() -> None:
    assert "create_project" in TOOL_REGISTRY


def test_nom_required() -> None:
    with pytest.raises(ValidationError):
        mod.CreateProjectPayload()  # type: ignore[call-arg]


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        mod.CreateProjectPayload(nom="x", rogue="y")  # type: ignore[call-arg]


def test_iso2_length_validated() -> None:
    with pytest.raises(ValidationError):
        mod.CreateProjectPayload(nom="x", localisation_pays_iso2="SEN")


def test_handle_calls_service_with_llm_source(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class _Row:
        id = UUID("00000000-0000-0000-0000-000000000abc")
        version = 1
        statut = "brouillon"

    def fake_create_projet(db: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return _Row()

    monkeypatch.setattr(mod, "create_projet", fake_create_projet)

    payload = mod.CreateProjectPayload(
        nom="Panneaux solaires Nord",
        montant_recherche={"amount": "5000000", "currency": "EUR"},
    )
    result = mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id=uuid4(),
        user_id=uuid4(),
        payload=payload,
    )

    assert result["created"] is True
    assert result["statut"] == "brouillon"
    assert captured["source_of_change"] == SourceOfChange.LLM
    assert captured["payload"]["nom"] == "Panneaux solaires Nord"
    assert captured["payload"]["montant_recherche"]["currency"] == "EUR"


def test_handle_minimal_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class _Row:
        id = UUID("00000000-0000-0000-0000-0000000000aa")
        version = 1
        statut = "brouillon"

    def fake_create_projet(db: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return _Row()

    monkeypatch.setattr(mod, "create_projet", fake_create_projet)

    payload = mod.CreateProjectPayload(nom="X")
    result = mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id="acc-1",
        user_id="u-1",
        payload=payload,
    )
    assert result["created"] is True
    assert "montant_recherche" not in captured["payload"]
