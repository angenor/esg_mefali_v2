"""F52 US2 — Tests des schémas Pydantic pour /parametres."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.users.schemas_f52 import (
    AccountDeletionCreate,
    EmailChangeRequest,
    NotificationPreferenceItem,
    NotificationPreferencesUpdate,
)


class TestNotificationPreferenceItem:
    def test_basic(self) -> None:
        m = NotificationPreferenceItem(
            kind="deadline_j_minus_30", channel="email", enabled=False
        )
        assert m.enabled is False

    def test_invalid_channel(self) -> None:
        with pytest.raises(ValidationError):
            NotificationPreferenceItem(
                kind="deadline_j_minus_30", channel="sms", enabled=True
            )  # type: ignore[arg-type]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            NotificationPreferenceItem(
                kind="deadline_j_minus_30",
                channel="email",
                enabled=True,
                extra="x",
            )  # type: ignore[call-arg]


class TestNotificationPreferencesUpdate:
    def test_min_length(self) -> None:
        with pytest.raises(ValidationError):
            NotificationPreferencesUpdate(updates=[])

    def test_max_length(self) -> None:
        items = [
            {"kind": "deadline_j_minus_30", "channel": "email", "enabled": True}
        ] * 51
        with pytest.raises(ValidationError):
            NotificationPreferencesUpdate(updates=items)  # type: ignore[arg-type]


class TestEmailChangeRequest:
    def test_email_format(self) -> None:
        m = EmailChangeRequest(new_email="user@example.com", current_password="p" * 8)
        assert m.new_email == "user@example.com"

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            EmailChangeRequest(
                new_email="not-an-email", current_password="x" * 8
            )

    def test_password_secret(self) -> None:
        m = EmailChangeRequest(new_email="a@b.fr", current_password="secret123")
        # SecretStr cache la valeur
        assert "secret" not in repr(m)


class TestAccountDeletionCreate:
    def test_minimal(self) -> None:
        m = AccountDeletionCreate(confirmation_text="ACME SARL")
        assert m.confirmation_text == "ACME SARL"
        assert m.reason_motif is None

    def test_motif_max_length(self) -> None:
        with pytest.raises(ValidationError):
            AccountDeletionCreate(
                confirmation_text="x", reason_motif="a" * 1025
            )

    def test_confirmation_text_required(self) -> None:
        with pytest.raises(ValidationError):
            AccountDeletionCreate(confirmation_text="")
