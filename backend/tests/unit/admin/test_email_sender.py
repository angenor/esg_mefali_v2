"""F10 T017 — unit tests for the EmailSender abstraction."""

from __future__ import annotations

import pytest

from app.email.sender import (
    ConsoleEmailSender,
    EmailMessage,
    EmailSender,
    ResendEmailSender,
)


def test_email_message_is_immutable() -> None:
    m = EmailMessage(to="x@y.z", subject="s", html="<p/>")
    with pytest.raises(Exception):  # noqa: B017 — frozen dataclass raises FrozenInstanceError
        m.subject = "new"  # type: ignore[misc]


def test_console_sender_returns_id() -> None:
    s: EmailSender = ConsoleEmailSender()
    msg = EmailMessage(to="x@y.z", subject="hi", html="<p>hi</p>")
    out = s.send(msg)
    assert out.startswith("console-")


def test_resend_sender_deferred() -> None:
    s = ResendEmailSender(api_key="re_xxx", default_from="noreply@m")
    with pytest.raises(NotImplementedError):
        s.send(EmailMessage(to="x@y.z", subject="hi", html="<p/>"))
