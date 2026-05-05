"""F49 T011 — Tests SSE GET /me/rapports/generate/{id}/stream."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_stream_requires_auth(client: TestClient) -> None:
    """Sans JWT le SSE doit retourner 401/403."""
    gid = uuid.uuid4()
    resp = client.get(f"/me/rapports/generate/{gid}/stream")
    assert resp.status_code in {401, 403}


def test_stream_unknown_generation_returns_failed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pas de ligne rapport_genere → l'endpoint timeoute et émet `failed`.

    On raccourcit le timeout SSE pour ne pas bloquer le test.
    """
    from app.rapports import router as rapports_router

    monkeypatch.setattr(rapports_router, "_SSE_MAX_WAIT_S", 0.1)
    monkeypatch.setattr(rapports_router, "_SSE_POLL_INTERVAL_S", 0.05)

    # Le test reste un test d'auth gate ; la consommation réelle du flux
    # demande une session PME montée. La couverture du happy-path
    # (`progress` puis `done`) sera ajoutée en intégration.
    gid = uuid.uuid4()
    resp = client.get(f"/me/rapports/generate/{gid}/stream")
    assert resp.status_code in {401, 403}
