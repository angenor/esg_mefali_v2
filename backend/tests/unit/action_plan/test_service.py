"""F31 — Tests unitaires du service ActionPlanService (T010).

Couvre les chemins critiques avec une session SQLAlchemy mockée. Les
intégrations DB réelles sont en T012/T018-T020 (intégration).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.action_plan.enums import StepStatus
from app.action_plan.schemas import ActionStepPatch
from app.action_plan.service import (
    ActionPlanService,
    InvalidHorizonError,
    NoScoreCalculationError,
    StepNotFoundError,
)

# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #


def _fake_session_with_score(score_obj):
    """Mock de Session : 3 execute() consécutifs (score, lock, max(version))."""
    db = MagicMock()
    score_result = MagicMock()
    score_result.scalar_one_or_none.return_value = score_obj
    lock_result = MagicMock()
    lock_result.scalar.return_value = None
    max_result = MagicMock()
    max_result.scalar.return_value = 0  # première version → 1
    db.execute.side_effect = [score_result, lock_result, max_result]
    return db


def _fake_score(account_id: uuid.UUID, details_json: dict | None = None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        account_id=account_id,
        computed_at=datetime(2026, 4, 28, tzinfo=UTC),
        details_json=details_json or {"gaps": []},
    )


# --------------------------------------------------------------------------- #
#  Validation horizon                                                         #
# --------------------------------------------------------------------------- #


def test_generate_rejects_invalid_horizon() -> None:
    service = ActionPlanService(MagicMock())
    with pytest.raises(InvalidHorizonError):
        service.generate(account_id=uuid.uuid4(), horizon_months=8, user_id=None)


# --------------------------------------------------------------------------- #
#  No score → NoScoreCalculationError                                         #
# --------------------------------------------------------------------------- #


def test_generate_raises_when_no_score_calculation() -> None:
    db = MagicMock()
    score_result = MagicMock()
    score_result.scalar_one_or_none.return_value = None
    db.execute.return_value = score_result
    service = ActionPlanService(db)
    with pytest.raises(NoScoreCalculationError):
        service.generate(account_id=uuid.uuid4(), horizon_months=12, user_id=None)


# --------------------------------------------------------------------------- #
#  Generate happy path                                                        #
# --------------------------------------------------------------------------- #


@patch("app.action_plan.service.record_audit")
def test_generate_calls_record_audit_and_creates_default_step(
    audit_mock: MagicMock,
) -> None:
    account_id = uuid.uuid4()
    score = _fake_score(account_id, details_json={"gaps": []})
    db = _fake_session_with_score(score)
    service = ActionPlanService(db)
    plan = service.generate(account_id=account_id, horizon_months=12, user_id=None)

    assert plan.account_id == account_id
    assert plan.horizon_months == 12
    assert plan.version == 1
    assert plan.score_calculation_id == score.id
    audit_mock.assert_called_once()
    # add(plan) + add(default_step)
    assert db.add.call_count >= 2


@patch("app.action_plan.service.record_audit")
def test_generate_uses_score_details_to_build_steps(
    audit_mock: MagicMock,
) -> None:
    account_id = uuid.uuid4()
    score = _fake_score(
        account_id,
        details_json={
            "gaps": [
                {
                    "indicator_code": "S1",
                    "score_normalized": "0.10",
                    "pillar": "social",
                },
                {
                    "indicator_code": "S2",
                    "score_normalized": "0.50",
                    "pillar": "social",
                },
                {
                    "indicator_code": "S3",
                    "score_normalized": "0.75",
                    "pillar": "social",
                },
            ]
        },
    )
    db = _fake_session_with_score(score)
    service = ActionPlanService(db)
    service.generate(account_id=account_id, horizon_months=12, user_id=None)
    # 1 plan + 3 steps
    assert db.add.call_count == 4
    audit_mock.assert_called_once()


# --------------------------------------------------------------------------- #
#  update_step                                                                #
# --------------------------------------------------------------------------- #


def test_update_step_raises_when_step_missing() -> None:
    db = MagicMock()
    db.get.return_value = None
    service = ActionPlanService(db)
    with pytest.raises(StepNotFoundError):
        service.update_step(
            step_id=uuid.uuid4(),
            patch=ActionStepPatch(status=StepStatus.DOING),
            user_id=None,
            account_id=uuid.uuid4(),
        )


def test_update_step_raises_when_plan_owned_by_another_account() -> None:
    other_acc = uuid.uuid4()
    step = SimpleNamespace(
        id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        status="todo",
        responsible_user_id=None,
    )
    plan = SimpleNamespace(id=step.plan_id, account_id=other_acc)
    db = MagicMock()
    db.get.side_effect = [step, plan]
    service = ActionPlanService(db)
    with pytest.raises(StepNotFoundError):
        service.update_step(
            step_id=step.id,
            patch=ActionStepPatch(status=StepStatus.DOING),
            user_id=None,
            account_id=uuid.uuid4(),  # different account
        )


@patch("app.action_plan.service.record_audit")
def test_update_step_changes_status_and_audits(audit_mock: MagicMock) -> None:
    acc = uuid.uuid4()
    step = SimpleNamespace(
        id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        status="todo",
        responsible_user_id=None,
        updated_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    plan = SimpleNamespace(id=step.plan_id, account_id=acc)
    db = MagicMock()
    db.get.side_effect = [step, plan]
    service = ActionPlanService(db)
    out = service.update_step(
        step_id=step.id,
        patch=ActionStepPatch(status=StepStatus.DOING),
        user_id=uuid.uuid4(),
        account_id=acc,
    )
    assert out.status == "doing"
    audit_mock.assert_called_once()


@patch("app.action_plan.service.record_audit")
def test_update_step_no_op_when_status_unchanged(audit_mock: MagicMock) -> None:
    """Si aucun champ ne change, pas d'audit (no-op)."""
    acc = uuid.uuid4()
    step = SimpleNamespace(
        id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        status="doing",
        responsible_user_id=None,
        updated_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    plan = SimpleNamespace(id=step.plan_id, account_id=acc)
    db = MagicMock()
    db.get.side_effect = [step, plan]
    service = ActionPlanService(db)
    service.update_step(
        step_id=step.id,
        patch=ActionStepPatch(status=StepStatus.DOING),
        user_id=None,
        account_id=acc,
    )
    audit_mock.assert_not_called()


# --------------------------------------------------------------------------- #
#  get_current                                                                #
# --------------------------------------------------------------------------- #


def test_get_current_returns_none_when_no_plan() -> None:
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    service = ActionPlanService(db)
    assert service.get_current(account_id=uuid.uuid4()) is None


def test_get_current_returns_plan() -> None:
    db = MagicMock()
    fake_plan = SimpleNamespace(id=uuid.uuid4(), version=2)
    result = MagicMock()
    result.scalar_one_or_none.return_value = fake_plan
    db.execute.return_value = result
    service = ActionPlanService(db)
    out = service.get_current(account_id=uuid.uuid4())
    assert out is fake_plan
