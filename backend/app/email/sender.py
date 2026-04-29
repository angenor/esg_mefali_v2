"""F10 — EmailSender abstraction (T017).

Provider = Resend (production) ; ConsoleEmailSender en dev/tests.

The full Resend HTTP integration (httpx call, retry, ``email_delivery_log``
persistence) is wired in T018/T037 — DEFERRED in MVP. The Protocol below is
the stable seam used by US3/US4 services.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    """Immutable email envelope."""

    to: str
    subject: str
    html: str
    text: str | None = None
    reply_to: str | None = None


class EmailSender(Protocol):
    """Abstract email transport — implementations must be side-effect-only."""

    def send(self, message: EmailMessage) -> str:
        """Return a provider message id (or a synthetic id in dev)."""


class ConsoleEmailSender:
    """Dev/test implementation — logs the message and returns a stub id."""

    def send(self, message: EmailMessage) -> str:
        logger.info(
            "[ConsoleEmailSender] to=%s subject=%s", message.to, message.subject
        )
        return f"console-{hash((message.to, message.subject)) & 0xFFFFFF:06x}"


class ResendEmailSender:
    """Resend.com transport (placeholder).

    Concrete httpx call is DEFERRED to the full US3 implementation.
    """

    def __init__(self, api_key: str, default_from: str) -> None:
        self.api_key = api_key
        self.default_from = default_from

    def send(self, message: EmailMessage) -> str:  # pragma: no cover - DEFERRED
        raise NotImplementedError(
            "ResendEmailSender.send is DEFERRED to F10 US3 full implementation"
        )
