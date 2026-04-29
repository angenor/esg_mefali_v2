"""F31 — Tests unitaires des routes (T012/T018-T020 lite, sans DB).

Utilise FastAPI ``dependency_overrides`` + service patché pour valider les
sérialisations et les flux d'erreurs (404/422) sans toucher Postgres.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.action_plan.routes import router as ap_router
from app.action_plan.service import (
    ActionPlanService,
    NoScoreCalculationError,
    StepNotFoundError,
)
from app.auth.dependencies import get_current_pme
from app.db import get_db


def _fake_user(account_id: uuid.UUID | None = None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        account_id=account_id or uuid.uuid4(),
        role="pme",
    )


def _fake_step(plan_id: uuid.UUID, account_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        plan_id=plan_id,
        title="Combler ESG-1",
        description="desc",
        category="esg",
        priority="haute",
        horizon_at=date(2026, 8, 27),
        status="todo",
        responsible_user_id=None,
        indicateur_id=None,
        source_id=None,
        created_at=datetime(2026, 4, 29, tzinfo=UTC),
        updated_at=datetime(2026, 4, 29, tzinfo=UTC),
    )


def _fake_plan(account_id: uuid.UUID, with_steps: int = 1):
    pid = uuid.uuid4()
    plan = SimpleNamespace(
        id=pid,
        account_id=account_id,
        horizon_months=12,
        version=1,
        score_calculation_id=uuid.uuid4(),
        generated_at=datetime(2026, 4, 29, tzinfo=UTC),
        generated_by_user_id=None,
        steps=[_fake_step(pid, account_id) for _ in range(with_steps)],
    )
    return plan


@pytest.fixture()
def app_client() -> TestClient:
    """FastAPI minimal app with only the action_plan router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(ap_router)
    return TestClient(app, raise_server_exceptions=True)


# --------------------------------------------------------------------------- #
#  POST /me/action-plan/generate                                              #
# --------------------------------------------------------------------------- #


def test_generate_201_with_plan(app_client: TestClient, monkeypatch) -> None:
    user = _fake_user()
    plan = _fake_plan(user.account_id, with_steps=2)

    fake_service = MagicMock(spec=ActionPlanService)
    fake_service.generate.return_value = plan
    monkeypatch.setattr(
        "app.action_plan.routes.ActionPlanService", lambda db: fake_service
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()

    r = app_client.post("/me/action-plan/generate?horizon=12")
    assert r.status_code == 201
    body = r.json()
    assert body["version"] == 1
    assert body["horizon_months"] == 12
    assert len(body["steps"]) == 2


def test_generate_422_when_no_score(app_client: TestClient, monkeypatch) -> None:
    user = _fake_user()
    fake_service = MagicMock(spec=ActionPlanService)
    fake_service.generate.side_effect = NoScoreCalculationError("Aucun score")
    monkeypatch.setattr(
        "app.action_plan.routes.ActionPlanService", lambda db: fake_service
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()

    r = app_client.post("/me/action-plan/generate?horizon=12")
    assert r.status_code == 422
    assert "Aucun score" in r.json()["detail"]


def test_generate_422_when_horizon_invalid(app_client: TestClient) -> None:
    user = _fake_user()
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    r = app_client.post("/me/action-plan/generate?horizon=8")
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
#  GET /me/action-plan                                                        #
# --------------------------------------------------------------------------- #


def test_get_current_404_when_no_plan(
    app_client: TestClient, monkeypatch
) -> None:
    user = _fake_user()
    fake_service = MagicMock(spec=ActionPlanService)
    fake_service.get_current.return_value = None
    monkeypatch.setattr(
        "app.action_plan.routes.ActionPlanService", lambda db: fake_service
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    r = app_client.get("/me/action-plan")
    assert r.status_code == 404


def test_get_current_200_with_plan(
    app_client: TestClient, monkeypatch
) -> None:
    user = _fake_user()
    plan = _fake_plan(user.account_id, with_steps=1)
    fake_service = MagicMock(spec=ActionPlanService)
    fake_service.get_current.return_value = plan
    monkeypatch.setattr(
        "app.action_plan.routes.ActionPlanService", lambda db: fake_service
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    r = app_client.get("/me/action-plan")
    assert r.status_code == 200
    assert r.json()["version"] == 1


# --------------------------------------------------------------------------- #
#  PATCH /me/action-plan/steps/{id}                                           #
# --------------------------------------------------------------------------- #


def test_patch_step_422_on_empty_payload(app_client: TestClient) -> None:
    user = _fake_user()
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    sid = uuid.uuid4()
    r = app_client.patch(f"/me/action-plan/steps/{sid}", json={})
    assert r.status_code == 422


def test_patch_step_404_when_unknown(
    app_client: TestClient, monkeypatch
) -> None:
    user = _fake_user()
    fake_service = MagicMock(spec=ActionPlanService)
    fake_service.update_step.side_effect = StepNotFoundError("nope")
    monkeypatch.setattr(
        "app.action_plan.routes.ActionPlanService", lambda db: fake_service
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    sid = uuid.uuid4()
    r = app_client.patch(
        f"/me/action-plan/steps/{sid}", json={"status": "doing"}
    )
    assert r.status_code == 404


def test_patch_step_200_when_valid(
    app_client: TestClient, monkeypatch
) -> None:
    user = _fake_user()
    step = _fake_step(uuid.uuid4(), user.account_id)
    step.status = "doing"
    fake_service = MagicMock(spec=ActionPlanService)
    fake_service.update_step.return_value = step
    monkeypatch.setattr(
        "app.action_plan.routes.ActionPlanService", lambda db: fake_service
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    r = app_client.patch(
        f"/me/action-plan/steps/{step.id}", json={"status": "doing"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "doing"


def test_patch_step_422_on_invalid_status_enum(app_client: TestClient) -> None:
    user = _fake_user()
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    sid = uuid.uuid4()
    r = app_client.patch(
        f"/me/action-plan/steps/{sid}", json={"status": "blocked"}
    )
    assert r.status_code == 422


def test_patch_step_422_on_unknown_field(app_client: TestClient) -> None:
    user = _fake_user()
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    sid = uuid.uuid4()
    r = app_client.patch(f"/me/action-plan/steps/{sid}", json={"foo": "bar"})
    assert r.status_code == 422
