"""F58 — Ops alerting (FR-022, FR-023).

Helper ``send_alert(...)`` qui POSTe un payload Slack Block Kit sur le
webhook ``OPS_SLACK_WEBHOOK_URL``. Si la variable d'env n'est pas définie,
no-op silencieux + log ERROR (jamais d'exception remontée).

Garde-fous :
- timeout 5 s, 1 retry exponentiel ;
- coalescence in-memory : max 1 alerte du même ``title`` par 5 min ;
- aucune exception ne remonte (réseau, parsing, indisponibilité Slack).
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Mapping
from time import monotonic
from typing import Final, Literal

logger = logging.getLogger(__name__)

Severity = Literal["info", "warning", "critical"]

_COALESCE_WINDOW_S: Final[float] = 300.0
_LAST_ALERT_BY_TITLE: dict[str, float] = {}

_SEVERITY_COLORS: Final[dict[Severity, str]] = {
    "info": "#3498db",
    "warning": "#f1c40f",
    "critical": "#e74c3c",
}

_SLACK_TIMEOUT_S: Final[float] = 5.0


def _should_coalesce(title: str) -> bool:
    """True si une alerte du même ``title`` a été envoyée < 5 min auparavant."""
    now = monotonic()
    last = _LAST_ALERT_BY_TITLE.get(title)
    if last is not None and (now - last) < _COALESCE_WINDOW_S:
        return True
    _LAST_ALERT_BY_TITLE[title] = now
    return False


def _build_payload(
    *, severity: Severity, title: str, message: str, fields: Mapping[str, str] | None
) -> dict:
    """Construit un payload Slack Block Kit minimal."""
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"[{severity.upper()}] {title}"},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": message}},
    ]
    if fields:
        fields_md = [
            {"type": "mrkdwn", "text": f"*{k}*\n{v}"} for k, v in fields.items()
        ]
        # Slack accepte 10 fields max par section
        blocks.append({"type": "section", "fields": fields_md[:10]})
    return {
        "attachments": [
            {
                "color": _SEVERITY_COLORS.get(severity, "#3498db"),
                "blocks": blocks,
            }
        ]
    }


async def send_alert(
    *,
    severity: Severity,
    title: str,
    message: str,
    fields: Mapping[str, str] | None = None,
) -> None:
    """Poste l'alerte sur Slack si webhook configuré, sinon log ERROR.

    Coalescence : 1 alerte par ``title`` toutes les 5 min.
    Aucune exception ne remonte au caller.
    """
    if _should_coalesce(title):
        logger.debug("alert coalesced (window=300s): %s", title)
        return

    webhook = os.environ.get("OPS_SLACK_WEBHOOK_URL", "").strip()
    payload = _build_payload(
        severity=severity, title=title, message=message, fields=fields
    )

    if not webhook:
        logger.error(
            "ops_alert (no slack configured) severity=%s title=%s message=%s",
            severity,
            title,
            message,
        )
        return

    # Import paresseux pour ne charger httpx qu'au besoin
    try:
        import httpx
    except Exception:  # pragma: no cover
        logger.error("httpx not available; alert lost: %s", title)
        return

    async def _post_once() -> None:
        async with httpx.AsyncClient(timeout=_SLACK_TIMEOUT_S) as client:
            r = await client.post(webhook, json=payload)
            r.raise_for_status()

    # 1 retry exponentiel (FR-022)
    for attempt in (0, 1):
        try:
            await _post_once()
            return
        except Exception:  # noqa: BLE001
            logger.debug("Slack alert attempt %d failed", attempt + 1, exc_info=True)
            if attempt == 0:
                await asyncio.sleep(0.5)
            continue
    # Final fallback : log ERROR (jamais bloquer le flux)
    logger.error("ops_alert failed after retry: %s — %s", title, message)


def _reset_coalesce_cache() -> None:
    """Réservé aux tests."""
    _LAST_ALERT_BY_TITLE.clear()


__all__ = ["Severity", "_reset_coalesce_cache", "send_alert"]
