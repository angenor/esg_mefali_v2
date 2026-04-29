"""T018 — Tests politique mot de passe (≥12 chars, 1 maj, 1 min, 1 chiffre)."""

from __future__ import annotations

import pytest

from app.core.security import PasswordPolicyError, validate_password_policy


@pytest.mark.parametrize(
    "password",
    [
        "Sup3rSecret!Pass",
        "Abcdefghijk1",
        "0Abcdefghijk",
        "ZzzzzzzzzzzZ1",
    ],
)
def test_valid_passwords(password):
    validate_password_policy(password)  # ne lève pas


@pytest.mark.parametrize(
    "password,reason_substr",
    [
        ("short1A", "12"),
        ("alllowercase1aaaaaa", "majuscule"),
        ("ALLUPPERCASE1AAAAAA", "minuscule"),
        ("NoDigitsHereAaaaaaa", "chiffre"),
        ("", "12"),
    ],
)
def test_invalid_passwords(password, reason_substr):
    with pytest.raises(PasswordPolicyError) as exc:
        validate_password_policy(password)
    assert reason_substr.lower() in str(exc.value).lower()


def test_too_long_password_rejected():
    with pytest.raises(PasswordPolicyError):
        validate_password_policy("A1a" + "x" * 200)
