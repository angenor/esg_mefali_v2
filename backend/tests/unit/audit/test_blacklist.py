"""F04 — Unit tests for audit field-blacklist redaction (T032, SC-010)."""

from __future__ import annotations

import pytest

from app.audit.blacklist import AUDIT_REDACTION_FIELDS, REDACTED, redact, redact_field


class TestRedaction:
    @pytest.mark.parametrize("field", AUDIT_REDACTION_FIELDS)
    def test_top_level_blacklist(self, field: str) -> None:
        assert redact_field(field, "secret-value") == REDACTED

    def test_top_level_field_not_in_blacklist_passes_through(self) -> None:
        assert redact_field("description", "hello") == "hello"
        assert redact_field("amount", 42) == 42

    def test_depth_1_dict(self) -> None:
        out = redact({"name": "Alice", "password": "p4ss"})
        assert out == {"name": "Alice", "password": REDACTED}

    def test_depth_2_nested_dict(self) -> None:
        out = redact({"profile": {"jwt": "tok", "email": "a@b"}})
        assert out["profile"]["jwt"] == REDACTED
        assert out["profile"]["email"] == "a@b"

    def test_depth_3_nested_list_of_dicts(self) -> None:
        out = redact(
            {
                "tokens": [
                    {"id": 1, "access_token": "AAA"},
                    {"id": 2, "secret": "BBB"},
                ]
            }
        )
        assert out["tokens"][0]["access_token"] == REDACTED
        assert out["tokens"][1]["secret"] == REDACTED
        assert out["tokens"][0]["id"] == 1

    def test_partial_match_password_hash(self) -> None:
        out = redact({"user_password_hash": "x"})
        assert out["user_password_hash"] == REDACTED

    def test_immutability(self) -> None:
        original = {"password": "p"}
        out = redact(original)
        assert original == {"password": "p"}  # unchanged
        assert out["password"] == REDACTED

    def test_preserves_lists_and_tuples(self) -> None:
        assert redact([1, 2, 3]) == [1, 2, 3]
        assert redact((1, 2)) == (1, 2)

    def test_redact_field_blacklisted_dict_value(self) -> None:
        # Field is itself blacklisted -> entire (possibly structured) value redacted.
        assert redact_field("api_key", {"prefix": "pk_", "value": "abc"}) == REDACTED
