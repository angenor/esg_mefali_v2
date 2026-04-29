"""F17 US1 — Tests ``update_company_profile``."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.audit.schemas import SourceOfChange
from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.mutations import update_company_profile as mod
from app.orchestrator.tools.mutations._rate_limit import reset_rate_limit_state


@pytest.fixture(autouse=True)
def _setup() -> None:
    reset_rate_limit_state()
    mod.register()
    yield
    reset_rate_limit_state()


def test_register_adds_tool() -> None:
    assert "update_company_profile" in TOOL_REGISTRY


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        mod.UpdateCompanyProfilePayload(
            fields={"taille_effectifs": 75, "rogue": "x"},  # type: ignore[arg-type]
            expected_version=1,
        )


def test_unknown_field_rejected() -> None:
    with pytest.raises(ValidationError):
        mod.UpdateCompanyProfileFields(unknown_field="x")  # type: ignore[call-arg]


def test_iso2_length_validated() -> None:
    with pytest.raises(ValidationError):
        mod.UpdateCompanyProfileFields(localisation_siege_pays_iso2="SEN")


def test_money_input_extra_rejected() -> None:
    with pytest.raises(ValidationError):
        mod.MoneyInput(amount=Decimal("1"), currency="USD", extra="x")  # type: ignore[call-arg]


def test_negative_effectifs_rejected() -> None:
    with pytest.raises(ValidationError):
        mod.UpdateCompanyProfileFields(taille_effectifs=-1)


def test_handle_no_fields_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_update_partial(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("ne doit pas être appelé")

    monkeypatch.setattr(mod, "update_partial", fake_update_partial)

    payload = mod.UpdateCompanyProfilePayload(fields={}, expected_version=1)
    result = mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id=uuid4(),
        user_id=uuid4(),
        payload=payload,
    )
    assert result == {"updated": False, "reason": "no_fields_provided"}


def test_handle_calls_service_with_llm_source(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class _Row:
        id = UUID("00000000-0000-0000-0000-000000000123")
        version = 2

    def fake_update_partial(db: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return _Row()

    monkeypatch.setattr(mod, "update_partial", fake_update_partial)

    payload = mod.UpdateCompanyProfilePayload(
        fields={"taille_effectifs": 75}, expected_version=1
    )
    result = mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id="acc-1",
        user_id="u-1",
        payload=payload,
    )

    assert result["updated"] is True
    assert result["version"] == 2
    assert "taille_effectifs" in result["fields_changed"]
    assert captured["source_of_change"] == SourceOfChange.LLM
    assert captured["expected_version"] == 1


def test_handle_unwraps_money_input(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class _Row:
        id = UUID("00000000-0000-0000-0000-000000000999")
        version = 3

    def fake_update_partial(db: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return _Row()

    monkeypatch.setattr(mod, "update_partial", fake_update_partial)

    payload = mod.UpdateCompanyProfilePayload(
        fields={"taille_ca": {"amount": "250000000", "currency": "XOF"}},
        expected_version=1,
    )
    mod.handle(
        db=None,  # type: ignore[arg-type]
        account_id="acc-1",
        user_id="u-1",
        payload=payload,
    )
    money = captured["payload"]["taille_ca"]
    assert money["currency"] == "XOF"
    assert str(money["amount"]) == "250000000"
