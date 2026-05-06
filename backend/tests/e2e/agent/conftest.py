"""Fixtures E2E pour les tests agent F54.

Fournit ``e2e_pme_session`` : un dict contenant les cookies httpx et le token
CSRF issus d'une inscription + connexion réelle contre le backend local.

Le backend doit être démarré sur E2E_BASE_URL avant l'exécution.
"""

from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

_BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8010")


@pytest.fixture(scope="session")
def e2e_pme_session() -> dict:
    """Crée un compte PME temporaire, se connecte, renvoie un dict avec :
    - ``cookies`` : dict de cookies httpx (mefali_at, mefali_csrf, mefali_rt)
    - ``csrf_token`` : valeur du cookie CSRF à envoyer en header x-csrf-token
    - ``access_token`` : valeur brute du cookie mefali_at (pour compat)
    """
    email = f"e2e_pme_{int(time.time())}_{uuid.uuid4().hex[:6]}@example.com"
    password = "E2eTestPass123!"

    with httpx.Client(base_url=_BASE_URL, timeout=30.0) as client:
        # Inscription (register renvoie directement les cookies de session)
        r = client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
        if r.status_code not in (200, 201):
            pytest.fail(
                f"Impossible d'inscrire le compte E2E PME ({r.status_code}): {r.text}"
            )

        cookies: dict = dict(client.cookies)
        csrf_token = cookies.get("mefali_csrf", "")
        access_token = cookies.get("mefali_at", "")

        if not csrf_token or not access_token:
            pytest.fail(
                f"Cookies de session absents après register: {list(cookies.keys())}"
            )

    return {
        "cookies": cookies,
        "csrf_token": csrf_token,
        "access_token": access_token,
        "email": email,
    }
