"""Tests embeddings_client (T048)."""

from __future__ import annotations

import pytest


def test_embed_raises_runtime_error_when_voyage_key_missing(monkeypatch):
    """T048 — pop VOYAGE_API_KEY → RuntimeError mentionnant VOYAGE_API_KEY."""
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    from app.embeddings_client import embed

    with pytest.raises(RuntimeError, match="VOYAGE_API_KEY"):
        embed(["test"])


def test_embed_raises_value_error_on_empty_input():
    from app.embeddings_client import embed

    with pytest.raises(ValueError):
        embed([])


def test_embed_success_with_mocked_http(monkeypatch):
    """embed retourne les embeddings parsés du payload Voyage."""
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key")
    from app import embeddings_client as ec

    class _FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {"data": [{"embedding": [0.1] * 1024}, {"embedding": [0.2] * 1024}]}

        text = ""

    def _fake_post(url, json, headers, timeout):
        assert url == ec.VOYAGE_API_URL
        assert headers["Authorization"] == "Bearer fake-key"
        assert json["model"] == ec.VOYAGE_MODEL
        return _FakeResp()

    monkeypatch.setattr(ec.httpx, "post", _fake_post)
    out = ec.embed(["a", "b"])
    assert len(out) == 2
    assert all(len(v) == 1024 for v in out)


def test_embed_raises_voyage_error_on_http_500(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key")
    from app import embeddings_client as ec

    class _Resp:
        status_code = 500
        text = "boom"

    monkeypatch.setattr(ec.httpx, "post", lambda *a, **k: _Resp())
    with pytest.raises(ec.VoyageError):
        ec.embed(["x"])


def test_embed_raises_voyage_error_on_network_failure(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-key")
    from app import embeddings_client as ec

    def _boom(*a, **k):
        raise ec.httpx.ConnectError("network down")

    monkeypatch.setattr(ec.httpx, "post", _boom)
    with pytest.raises(ec.VoyageError):
        ec.embed(["x"])
