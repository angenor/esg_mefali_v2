"""F56 / T033 — Tests unit du validator (FR-002).

Couvre :
- 4 décisions ``accept``, ``retry``, ``fallback``, ``annotate``.
- Mode ``off`` court-circuit → toujours ``accept``.
- Couverture par paragraphe (cumulative).
- Retry count = 1 → fallback.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from app.agent.sourcing.tool_schemas import CiteSourceArgs, FlagUnsourcedArgs
from app.agent.sourcing.validator import validate_response
from app.agent.state import ValidatedToolCall


def _cite(source_id=None) -> ValidatedToolCall:
    return ValidatedToolCall(
        id=str(uuid4()),
        name="cite_source",
        arguments=CiteSourceArgs(source_id=source_id or uuid4()),
    )


def _flag(claim: str = "x", reason: str = "y") -> ValidatedToolCall:
    return ValidatedToolCall(
        id=str(uuid4()),
        name="flag_unsourced",
        arguments=FlagUnsourcedArgs(claim=claim, reason=reason),
    )


class _DummyArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _other_call(name: str = "show_kpi") -> ValidatedToolCall:
    return ValidatedToolCall(
        id=str(uuid4()),
        name=name,
        arguments=_DummyArgs(),
    )


@pytest.mark.unit
def test_off_mode_short_circuits_to_accept() -> None:
    res = validate_response(
        "Le seuil GCF est 50 M USD.",
        tool_calls=[],
        mode="off",
    )
    assert res.decision == "accept"
    assert res.unsourced_claims == []


@pytest.mark.unit
def test_strict_with_no_factual_claim_accepts() -> None:
    res = validate_response(
        "Bonjour, comment ça va ?",
        tool_calls=[],
        mode="strict",
    )
    assert res.decision == "accept"
    assert res.unsourced_claims == []


@pytest.mark.unit
def test_strict_with_unsourced_factual_claim_retries_first_pass() -> None:
    res = validate_response(
        "Le seuil GCF est de 50 M USD.",
        tool_calls=[],
        mode="strict",
        sourcing_retry_count=0,
    )
    assert res.decision == "retry"
    assert len(res.unsourced_claims) >= 1


@pytest.mark.unit
def test_strict_with_unsourced_after_retry_falls_back() -> None:
    res = validate_response(
        "Le seuil GCF est de 50 M USD.",
        tool_calls=[],
        mode="strict",
        sourcing_retry_count=1,
    )
    assert res.decision == "fallback"


@pytest.mark.unit
def test_permissive_with_unsourced_annotates() -> None:
    res = validate_response(
        "Le seuil GCF est de 50 M USD.",
        tool_calls=[],
        mode="permissive",
    )
    assert res.decision == "annotate"


@pytest.mark.unit
def test_strict_with_cite_source_in_paragraph_accepts() -> None:
    """Un cite_source dans le tour couvre la portion."""
    res = validate_response(
        "Le seuil GCF est de 50 M USD.",
        tool_calls=[_cite()],
        mode="strict",
    )
    assert res.decision == "accept"
    assert res.unsourced_claims == []


@pytest.mark.unit
def test_strict_paragraph_cumulative_coverage() -> None:
    """Couverture cumulative : 2 paragraphes, 1 cite_source en p1 → couvre p1 et p2."""
    text = (
        "Le seuil GCF est de 50 M USD.\n\n"
        "Le facteur ADEME est de 6.0 kg CO2/litre."
    )
    # 1 cite_source pour p1 ⇒ couvre p1 et p2 (cumulative)
    res = validate_response(
        text,
        tool_calls=[_cite()],
        mode="strict",
    )
    assert res.decision == "accept"


@pytest.mark.unit
def test_strict_from_tool_excluded_from_unsourced() -> None:
    """Un claim ``from_tool=True`` ne doit pas déclencher de retry."""
    res = validate_response(
        "Vous avez 12 kWh enregistrés.",
        tool_calls=[],
        tool_outputs=["Mesure : 12 kWh stockée"],
        mode="strict",
    )
    assert res.decision == "accept"


@pytest.mark.unit
def test_validator_records_duration_ms() -> None:
    res = validate_response(
        "Le seuil GCF est 50 M USD.",
        tool_calls=[],
        mode="strict",
    )
    assert res.duration_ms >= 0


@pytest.mark.unit
def test_validator_returns_full_pydantic_shape() -> None:
    res = validate_response(
        "Le seuil GCF est 50 M USD.",
        tool_calls=[],
        mode="strict",
    )
    # Must serialize cleanly
    payload = res.model_dump()
    assert "claims_detected" in payload
    assert "citations_found" in payload
    assert "unsourced_claims" in payload
    assert payload["mode"] == "strict"


@pytest.mark.unit
def test_non_cite_calls_ignored_in_citations_found() -> None:
    res = validate_response(
        "Le seuil GCF est 50 M USD.",
        tool_calls=[_other_call("show_kpi"), _flag()],
        mode="strict",
    )
    # show_kpi et flag_unsourced ne sont pas des citations
    assert all(c.tool_call_id != _other_call("show_kpi").id for c in res.citations_found)
    # Aucun cite_source → retry
    assert res.decision == "retry"
