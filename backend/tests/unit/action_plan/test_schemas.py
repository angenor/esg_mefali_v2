"""F31 — Tests unitaires des schemas Pydantic v2 (T011)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.action_plan.enums import Category, Horizon, Priority, StepStatus
from app.action_plan.schemas import (
    ActionPlanRead,
    ActionStepPatch,
    ActionStepRead,
)


def _step_payload(**overrides) -> dict:
    payload = dict(
        id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        title="Combler ESG-1",
        description="desc",
        category=Category.ESG,
        priority=Priority.HAUTE,
        horizon_at=date(2026, 8, 27),
        status=StepStatus.TODO,
        responsible_user_id=None,
        indicateur_id=None,
        source_id=None,
        created_at=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
    )
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------- #
#  ActionStepPatch                                                            #
# --------------------------------------------------------------------------- #


def test_action_step_patch_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ActionStepPatch.model_validate({"foo": "bar"})


def test_action_step_patch_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ActionStepPatch.model_validate({"status": "blocked"})


def test_action_step_patch_accepts_valid_status() -> None:
    p = ActionStepPatch.model_validate({"status": "doing"})
    assert p.status == StepStatus.DOING
    assert p.has_any_field() is True


def test_action_step_patch_accepts_responsible_user_id() -> None:
    uid = uuid.uuid4()
    p = ActionStepPatch.model_validate({"responsible_user_id": str(uid)})
    assert p.responsible_user_id == uid
    assert p.has_any_field() is True


def test_action_step_patch_empty_payload_has_no_fields() -> None:
    p = ActionStepPatch.model_validate({})
    assert p.has_any_field() is False


def test_action_step_patch_allows_explicit_null_responsible() -> None:
    p = ActionStepPatch.model_validate({"responsible_user_id": None})
    assert p.responsible_user_id is None
    assert p.has_any_field() is True


# --------------------------------------------------------------------------- #
#  ActionStepRead                                                             #
# --------------------------------------------------------------------------- #


def test_action_step_read_validates_min_title_length() -> None:
    with pytest.raises(ValidationError):
        ActionStepRead.model_validate(_step_payload(title="ab"))


def test_action_step_read_round_trip_serialization() -> None:
    s = ActionStepRead.model_validate(_step_payload())
    dumped = s.model_dump(mode="json")
    assert dumped["status"] == "todo"
    assert dumped["category"] == "esg"
    assert dumped["priority"] == "haute"
    assert dumped["horizon_at"] == "2026-08-27"


# --------------------------------------------------------------------------- #
#  ActionPlanRead                                                             #
# --------------------------------------------------------------------------- #


def test_action_plan_read_horizon_must_be_in_enum() -> None:
    base = dict(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        horizon_months=8,  # invalid
        version=1,
        score_calculation_id=None,
        generated_at=datetime(2026, 4, 29, tzinfo=UTC),
        generated_by_user_id=None,
        steps=[],
    )
    with pytest.raises(ValidationError):
        ActionPlanRead.model_validate(base)


def test_action_plan_read_version_must_be_positive() -> None:
    base = dict(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        horizon_months=Horizon.TWELVE,
        version=0,  # invalid
        generated_at=datetime(2026, 4, 29, tzinfo=UTC),
        steps=[],
    )
    with pytest.raises(ValidationError):
        ActionPlanRead.model_validate(base)


def test_action_plan_read_accepts_valid_payload() -> None:
    plan = ActionPlanRead(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        horizon_months=Horizon.TWELVE,
        version=1,
        generated_at=datetime(2026, 4, 29, tzinfo=UTC),
        steps=[ActionStepRead.model_validate(_step_payload())],
    )
    dumped = plan.model_dump(mode="json")
    assert dumped["horizon_months"] == 12
    assert len(dumped["steps"]) == 1
