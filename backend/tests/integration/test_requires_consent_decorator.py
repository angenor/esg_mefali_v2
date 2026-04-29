"""F05 T032 — RequiresConsent dependency: 403 when consent missing."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.decorators.requires_consent import RequiresConsent
from app.main import app as main_app  # noqa: F401 — keeps import side-effects
from app.middleware.auth_session import AuthSessionMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.schemas.consent import ConsentKind
from tests.integration.conftest import requires_db


def _build_app() -> FastAPI:
    """Tiny app re-using the auth middleware + a guarded endpoint."""
    a = FastAPI()
    a.add_middleware(AuthSessionMiddleware)
    a.add_middleware(RequestIdMiddleware)

    # Inherit the auth/router so we can register/login here.
    from app.auth.router import router as auth_router

    a.include_router(auth_router)

    @a.get("/protected/mobile-money")
    def protected(_: None = Depends(RequiresConsent(ConsentKind.MOBILE_MONEY))) -> dict:
        return {"ok": True}

    return a


@pytest.fixture()
def guarded_client():
    a = _build_app()
    with TestClient(a) as c:
        yield c


@requires_db
def test_protected_endpoint_403_when_consent_off(
    guarded_client, unique_email, valid_password
):
    r = guarded_client.post(
        "/auth/register", json={"email": unique_email, "password": valid_password}
    )
    assert r.status_code in (200, 201)
    csrf = guarded_client.cookies.get("mefali_csrf")
    if csrf:
        guarded_client.headers["X-CSRF-Token"] = csrf

    r2 = guarded_client.get("/protected/mobile-money")
    assert r2.status_code == 403
    body = r2.json()
    detail = body.get("detail") or body
    assert detail.get("error") == "consent_required"
    assert detail.get("kind") == "mobile_money"


@requires_db
def test_protected_endpoint_200_when_consent_on(
    client, unique_email, valid_password
):
    """Use main app to flip the consent ON, then call protected endpoint."""
    # register on main app
    r = client.post(
        "/auth/register", json={"email": unique_email, "password": valid_password}
    )
    assert r.status_code in (200, 201)
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    r2 = client.post("/me/consentements/mobile_money", json={"given": True})
    assert r2.status_code == 200, r2.text
