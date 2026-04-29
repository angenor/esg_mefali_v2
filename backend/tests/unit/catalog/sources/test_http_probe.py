"""F07 — Tests unitaires HTTP HEAD probe (FR-007).

Le probe est non bloquant côté service : doit toujours renvoyer un dict
``{ok, status, error}`` sans relever d'exception.
"""

from __future__ import annotations

import httpx
import pytest

from app.catalog.sources.http_probe import probe_url


@pytest.mark.asyncio
async def test_probe_success_200():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    result = await probe_url("https://example.com/x", transport=transport)
    assert result["ok"] is True
    assert result["status"] == 200
    assert result["error"] is None


@pytest.mark.asyncio
async def test_probe_404_not_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    result = await probe_url("https://example.com/missing", transport=transport)
    assert result["ok"] is False
    assert result["status"] == 404
    assert result["error"] is None


@pytest.mark.asyncio
async def test_probe_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("boom")

    transport = httpx.MockTransport(handler)
    result = await probe_url("https://example.com/slow", transport=transport)
    assert result["ok"] is False
    assert result["status"] is None
    assert result["error"] == "timeout"


@pytest.mark.asyncio
async def test_probe_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns fail")

    transport = httpx.MockTransport(handler)
    result = await probe_url("https://nope.invalid/x", transport=transport)
    assert result["ok"] is False
    assert result["status"] is None
    assert result["error"] == "network"


@pytest.mark.asyncio
async def test_probe_redirect_followed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/r":
            return httpx.Response(
                301, headers={"Location": "https://example.com/final"}
            )
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    result = await probe_url("https://example.com/r", transport=transport)
    assert result["ok"] is True
    assert result["status"] == 200
