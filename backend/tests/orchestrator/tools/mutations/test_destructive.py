"""F17 — Tests décorateur ``@destructive`` (NFR-003)."""

from __future__ import annotations

from app.orchestrator.tools.mutations._destructive import (
    MutationConfirmationRequired,
    destructive,
)


def test_blocks_when_confirmed_missing() -> None:
    @destructive(tool_name="t", message="ok ?")
    def fn(**kwargs: object) -> str:
        return "executed"

    result = fn()
    assert isinstance(result, dict)
    assert result["requires_confirmation"] is True
    assert result["tool"] == "t"
    assert result["message"] == "ok ?"


def test_blocks_when_confirmed_false() -> None:
    @destructive(tool_name="t", message="m")
    def fn(**kwargs: object) -> str:
        return "executed"

    result = fn(confirmed=False)
    assert isinstance(result, dict)
    assert result["requires_confirmation"] is True


def test_executes_when_confirmed_true() -> None:
    @destructive(tool_name="t", message="m")
    def fn(**kwargs: object) -> str:
        return "executed"

    result = fn(confirmed=True)
    assert result == "executed"


def test_impact_is_returned() -> None:
    @destructive(tool_name="t", message="m", impact=("a", "b"))
    def fn(**kwargs: object) -> str:
        return "executed"

    result = fn()
    assert result["impact"] == ["a", "b"]


def test_payload_confirmed_is_observed() -> None:
    """Le décorateur lit ``payload.confirmed`` si confirmed kwarg absent."""

    class Payload:
        confirmed: bool = True

    @destructive(tool_name="t", message="m")
    def fn(**kwargs: object) -> str:
        return "executed"

    result = fn(payload=Payload())
    assert result == "executed"


def test_mutation_confirmation_required_to_dict() -> None:
    obj = MutationConfirmationRequired(
        requires_confirmation=True, tool="t", message="m", impact=("x",)
    )
    d = obj.to_dict()
    assert d["impact"] == ["x"]
    assert d["tool"] == "t"
