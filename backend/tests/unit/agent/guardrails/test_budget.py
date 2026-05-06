"""F58 / T048 — Tests unitaires budget (FR-013, FR-014, FR-015)."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.agent.guardrails.budget import (
    MAX_COMPLETION_TOKENS_PER_TURN,
    BudgetResult,
    _reset_cache,
    cap_completion_tokens,
    check_budget,
)


@pytest.mark.unit
def test_cap_completion_tokens_under_limit() -> None:
    assert cap_completion_tokens(4000) == 4000


@pytest.mark.unit
def test_cap_completion_tokens_at_limit() -> None:
    assert cap_completion_tokens(8000) == 8000


@pytest.mark.unit
def test_cap_completion_tokens_above_limit() -> None:
    assert cap_completion_tokens(10000) == 8000


@pytest.mark.unit
def test_cap_completion_tokens_custom_max() -> None:
    assert cap_completion_tokens(5000, max_per_turn=4000) == 4000


@pytest.mark.unit
def test_budget_result_is_immutable() -> None:
    br = BudgetResult(
        allowed=True,
        flow="conversation",
        requested_tokens=100,
        remaining_conversation_tokens=29900,
        remaining_ocr_analysis_tokens=20000,
        reason=None,
    )
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        br.allowed = False  # type: ignore[misc]


@pytest.mark.unit
def test_budget_result_refusal_has_french_reason() -> None:
    br = BudgetResult(
        allowed=False,
        flow="conversation",
        requested_tokens=10000,
        remaining_conversation_tokens=0,
        remaining_ocr_analysis_tokens=20000,
        reason="quota conversation atteint",
    )
    assert br.allowed is False
    assert br.reason is not None
    assert "quota" in br.reason.lower()


# ---------------------------------------------------------------------------
# check_budget — mocks SQL pour rester unit
# ---------------------------------------------------------------------------


def _mock_session(*, quota_total=50000, quota_conv=30000, quota_ocr=20000,
                  consumed_conv=0, consumed_ocr=0):
    """Mock SQLAlchemy session : 1ʳᵉ exec = quotas, 2ᵉ = consumed."""
    sess = MagicMock()

    quota_row = MagicMock()
    quota_row.first.return_value = {
        "tot": quota_total, "conv": quota_conv, "ocr": quota_ocr,
    }
    consumed_rows = []
    if consumed_conv:
        consumed_rows.append({"flow": "conversation", "tot": consumed_conv})
    if consumed_ocr:
        consumed_rows.append({"flow": "ocr_analysis", "tot": consumed_ocr})
    consumed_obj = MagicMock()
    consumed_obj.all.return_value = consumed_rows

    quotas_exec = MagicMock()
    quotas_exec.mappings.return_value = quota_row
    consumed_exec = MagicMock()
    consumed_exec.mappings.return_value = consumed_obj

    # Order matters : check_budget appelle d'abord _read_quotas puis _read_consumed
    sess.execute.side_effect = [quotas_exec, consumed_exec]
    return sess


@pytest.fixture(autouse=True)
def _reset_budget_cache():
    _reset_cache()
    yield
    _reset_cache()


@pytest.mark.unit
def test_check_budget_allowed_under_quota() -> None:
    sess = _mock_session(consumed_conv=1000)
    res = check_budget(sess, account_id=uuid4(), requested_tokens=500, flow="conversation")
    assert res.allowed is True
    assert res.flow == "conversation"
    assert res.remaining_conversation_tokens == 30000 - 1000
    assert res.reason is None


@pytest.mark.unit
def test_check_budget_refused_per_turn_cap() -> None:
    sess = _mock_session()
    res = check_budget(sess, account_id=uuid4(), requested_tokens=10000, flow="conversation")
    assert res.allowed is False
    assert res.reason is not None
    assert str(MAX_COMPLETION_TOKENS_PER_TURN) in res.reason


@pytest.mark.unit
def test_check_budget_refused_when_conversation_quota_exhausted() -> None:
    sess = _mock_session(consumed_conv=29800)
    res = check_budget(sess, account_id=uuid4(), requested_tokens=500, flow="conversation")
    # conv restant = 200, requested 500 → refusé
    assert res.allowed is False
    assert res.reason is not None
    assert "conversation" in res.reason.lower() or "quota" in res.reason.lower()


@pytest.mark.unit
def test_check_budget_ocr_independent_of_conversation() -> None:
    """Quota OCR ne se voit pas affecté quand conv épuisé (sous-quotas séparés)."""
    sess = _mock_session(consumed_conv=30000)
    res = check_budget(sess, account_id=uuid4(), requested_tokens=1000, flow="ocr_analysis")
    assert res.allowed is True


@pytest.mark.unit
def test_check_budget_refused_when_ocr_quota_exhausted() -> None:
    sess = _mock_session(consumed_ocr=19800)
    res = check_budget(sess, account_id=uuid4(), requested_tokens=500, flow="ocr_analysis")
    assert res.allowed is False
    assert res.reason is not None
    assert "ocr" in res.reason.lower() or "analyse" in res.reason.lower()


@pytest.mark.unit
def test_check_budget_handles_db_error_safely() -> None:
    """En cas d'erreur SQL, fallback sur defaults et autorise (jamais bloque le flux)."""
    sess = MagicMock()
    sess.execute.side_effect = Exception("DB down")
    res = check_budget(sess, account_id=uuid4(), requested_tokens=500, flow="conversation")
    # Avec defaults 30K et consommé fallback 0 → allowed
    assert res.allowed is True
