"""T019 — Tests unitaires des helpers de sécurité (bcrypt, JWT, CSRF, opaque)."""

from __future__ import annotations

import pytest

from app.core import security


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        h = security.hash_password("Sup3rSecret!Pass")
        assert h.startswith("$2b$") or h.startswith("$2a$")
        assert security.verify_password("Sup3rSecret!Pass", h) is True

    def test_verify_wrong_password(self):
        h = security.hash_password("Sup3rSecret!Pass")
        assert security.verify_password("nope", h) is False

    def test_hash_is_unique_each_time(self):
        a = security.hash_password("Sup3rSecret!Pass")
        b = security.hash_password("Sup3rSecret!Pass")
        assert a != b


class TestJWT:
    def test_create_decode_roundtrip(self):
        token = security.create_access_token({"sub": "abc", "role": "pme"}, ttl_seconds=60)
        payload = security.decode_access_token(token)
        assert payload["sub"] == "abc"
        assert payload["role"] == "pme"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token_raises(self):
        with pytest.raises(security.InvalidTokenError):
            security.decode_access_token("not.a.token")

    def test_expired_token_raises(self):
        token = security.create_access_token({"sub": "abc"}, ttl_seconds=-10)
        with pytest.raises(security.InvalidTokenError):
            security.decode_access_token(token)


class TestCSRF:
    def test_generate_csrf_token_unique(self):
        a = security.generate_csrf_token()
        b = security.generate_csrf_token()
        assert a != b
        assert len(a) >= 32

    def test_verify_csrf_token_match(self):
        t = security.generate_csrf_token()
        assert security.verify_csrf_token(t, t) is True

    def test_verify_csrf_token_mismatch(self):
        a = security.generate_csrf_token()
        b = security.generate_csrf_token()
        assert security.verify_csrf_token(a, b) is False

    def test_verify_csrf_token_empty_returns_false(self):
        assert security.verify_csrf_token("", "x") is False
        assert security.verify_csrf_token("x", "") is False


class TestOpaqueToken:
    def test_generate_opaque_token_url_safe(self):
        t = security.generate_opaque_token(32)
        assert isinstance(t, str)
        assert len(t) >= 32

    def test_sha256_hex_deterministic(self):
        h1 = security.sha256_hex("hello")
        h2 = security.sha256_hex("hello")
        assert h1 == h2
        assert len(h1) == 64
