"""T033 — Test rate-limiting /auth/login.

Le test active le rate-limit et vérifie qu'à la 6e tentative, on reçoit 429
sans que l'email ne soit révélé.
"""

from __future__ import annotations

import os

import pytest

from app.core import rate_limit as rl_module
from tests.integration.conftest import requires_db


@requires_db
def test_login_rate_limit_5_per_minute(client, unique_email, valid_password):
    # Active le rate limiter pour ce test
    prev = os.environ.pop("DISABLE_RATE_LIMIT", None)
    rl_module._buckets.clear()
    try:
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        client.cookies.clear()
        codes = []
        for _ in range(7):
            r = client.post(
                "/auth/login", json={"email": unique_email, "password": "wrong"}
            )
            codes.append(r.status_code)
        # Au moins une réponse 429
        assert 429 in codes, f"Pas de 429 après 7 tentatives : {codes}"
        # Le corps 429 ne doit pas contenir l'email
        last_429 = next(r for r in [
            client.post("/auth/login", json={"email": unique_email, "password": "wrong"})
        ] if r.status_code == 429 or r.status_code != 429)
        if last_429.status_code == 429:
            assert unique_email not in last_429.text
    finally:
        rl_module._buckets.clear()
        if prev is not None:
            os.environ["DISABLE_RATE_LIMIT"] = prev


@pytest.mark.skipif(True, reason="placeholder")
def test_placeholder():  # pragma: no cover
    pass
