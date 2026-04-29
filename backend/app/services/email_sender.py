"""F02 — Envoi d'email : interface ``EmailSender``, ``ConsoleEmailSender``,
``SMTPEmailSender``.

T016 — sélection via env ``EMAIL_BACKEND`` (``console`` | ``smtp``).
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    """Backend dev/test : log l'email dans la console (jamais le mot de passe)."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("[email:console] to=%s subject=%s body_len=%d", to, subject, len(body))


class SMTPEmailSender:
    """Backend production : envoi via aiosmtplib (synchroné via asyncio.run pour
    éviter de polluer toute la pile API en async strict).

    Conformité : ne jamais logger le contenu du body.
    """

    def __init__(self) -> None:
        s = get_settings()
        self._host = s.SMTP_HOST
        self._port = s.SMTP_PORT
        self._user = s.SMTP_USER
        self._password = s.SMTP_PASSWORD

    def send(self, *, to: str, subject: str, body: str) -> None:
        import asyncio
        from email.message import EmailMessage

        import aiosmtplib

        msg = EmailMessage()
        msg["From"] = self._user or "no-reply@mefali.example"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        async def _send() -> None:
            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._user or None,
                password=self._password or None,
                start_tls=True,
            )

        asyncio.run(_send())


def get_email_sender() -> EmailSender:
    """Factory : retourne l'EmailSender adapté au backend configuré."""
    backend = (get_settings().EMAIL_BACKEND or "console").lower()
    if backend == "smtp":
        return SMTPEmailSender()
    return ConsoleEmailSender()
