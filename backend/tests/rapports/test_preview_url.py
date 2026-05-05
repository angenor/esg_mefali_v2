"""F49 T012 — Tests endpoints preview-url + preview signé."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rapports.router import _sign_preview


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_preview_url_requires_auth(client: TestClient) -> None:
    """GET /me/rapports/{id}/preview-url exige une session PME."""
    rid = uuid.uuid4()
    resp = client.get(f"/me/rapports/{rid}/preview-url")
    assert resp.status_code in {401, 403}


def test_preview_with_invalid_signature_returns_404(
    client: TestClient,
) -> None:
    """Signature falsifiée → 404 (jamais 401/403)."""
    rid = uuid.uuid4()
    aid = uuid.uuid4()
    resp = client.get(
        f"/me/rapports/{rid}/preview",
        params={"aid": str(aid), "t": 9_999_999_999, "sig": "deadbeef"},
    )
    assert resp.status_code == 404


def test_preview_expired_signature_returns_404(client: TestClient) -> None:
    """Timestamp expiré → 404 même si signature serait correcte."""
    rid = uuid.uuid4()
    aid = uuid.uuid4()
    expired = 1
    sig = _sign_preview(rid, aid, expired)
    resp = client.get(
        f"/me/rapports/{rid}/preview",
        params={"aid": str(aid), "t": expired, "sig": sig},
    )
    assert resp.status_code == 404


def test_preview_signature_helper_is_deterministic() -> None:
    """`_sign_preview` doit être déterministe pour un même triplet."""
    rid = uuid.uuid4()
    aid = uuid.uuid4()
    t = 1_700_000_000
    assert _sign_preview(rid, aid, t) == _sign_preview(rid, aid, t)
    # Différent si un seul élément change
    assert _sign_preview(rid, aid, t) != _sign_preview(rid, aid, t + 1)
