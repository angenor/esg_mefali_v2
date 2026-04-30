"""F31 — Test contract OpenAPI (T013)."""

from __future__ import annotations

from app.main import app


def test_action_plan_routes_are_exposed_in_openapi() -> None:
    schema = app.openapi()
    paths = schema.get("paths", {})

    assert "/me/action-plan/generate" in paths
    assert "post" in paths["/me/action-plan/generate"]

    assert "/me/action-plan" in paths
    assert "get" in paths["/me/action-plan"]

    # FastAPI utilise {step_id} comme template de path
    step_path = next(
        (p for p in paths if p.startswith("/me/action-plan/steps/")), None
    )
    assert step_path is not None, "Le endpoint PATCH steps/{id} doit être exposé"
    assert "patch" in paths[step_path]


def test_generate_endpoint_returns_action_plan_read() -> None:
    schema = app.openapi()
    op = schema["paths"]["/me/action-plan/generate"]["post"]
    response_201 = op["responses"]["201"]
    content = response_201["content"]["application/json"]
    ref = content["schema"]["$ref"]
    assert ref.endswith("ActionPlanRead")


def test_patch_step_accepts_action_step_patch_body() -> None:
    schema = app.openapi()
    step_path = next(
        p for p in schema["paths"] if p.startswith("/me/action-plan/steps/")
    )
    op = schema["paths"][step_path]["patch"]
    ref = op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert ref.endswith("ActionStepPatch")
