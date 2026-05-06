"""F58 / T067 — Tests intégration ops_alerting (FR-022)."""

from __future__ import annotations

import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.ops_alerting import (
    _reset_coalesce_cache,
    send_alert,
)


@pytest.fixture(autouse=True)
def _reset() -> None:
    _reset_coalesce_cache()
    yield
    _reset_coalesce_cache()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_op_when_webhook_not_configured(
    caplog: pytest.LogCaptureFixture,
) -> None:
    os.environ.pop("OPS_SLACK_WEBHOOK_URL", None)
    with caplog.at_level(logging.ERROR):
        await send_alert(severity="critical", title="Test", message="no webhook")
    assert any("ops_alert" in r.message for r in caplog.records)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_posts_to_slack_when_configured() -> None:
    os.environ["OPS_SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/test"

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await send_alert(
            severity="critical",
            title="Circuit ouvert",
            message="LLM down",
            fields={"service": "openrouter"},
        )
    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "https://hooks.slack.com/services/test"
    payload = kwargs.get("json")
    assert "attachments" in payload
    os.environ.pop("OPS_SLACK_WEBHOOK_URL", None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coalescence_within_window() -> None:
    os.environ["OPS_SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/test"

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await send_alert(severity="info", title="X", message="1")
        await send_alert(severity="info", title="X", message="2")
        await send_alert(severity="info", title="X", message="3")
    # Une seule alerte effectivement postée (les 2 autres coalescées)
    assert mock_client.post.await_count == 1
    os.environ.pop("OPS_SLACK_WEBHOOK_URL", None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeout_does_not_raise(caplog: pytest.LogCaptureFixture) -> None:
    os.environ["OPS_SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/test"

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=TimeoutError("boom"))

    with patch("httpx.AsyncClient", return_value=mock_client), caplog.at_level(
        logging.ERROR
    ):
        # Ne doit pas lever
        await send_alert(severity="warning", title="Timeout test", message="x")
    # 2 tentatives (1 + 1 retry)
    assert mock_client.post.await_count == 2
    os.environ.pop("OPS_SLACK_WEBHOOK_URL", None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_payload_contains_severity_color() -> None:
    """Le payload contient une couleur cohérente avec la sévérité."""
    from app.utils.ops_alerting import _build_payload

    payload = _build_payload(
        severity="critical", title="t", message="m", fields=None
    )
    assert payload["attachments"][0]["color"] == "#e74c3c"

    payload2 = _build_payload(
        severity="warning", title="t", message="m", fields={"k": "v"}
    )
    assert payload2["attachments"][0]["color"] == "#f1c40f"
