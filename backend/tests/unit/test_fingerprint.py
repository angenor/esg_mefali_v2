"""F50 T007 — Tests unitaires de l'empreinte SHA-256 streaming."""

from __future__ import annotations

import hashlib
import io

import pytest

from app.storage.fingerprint import (
    is_valid_sha256_hex,
    sha256_bytes,
    sha256_stream,
)


@pytest.mark.unit
def test_sha256_bytes_empty() -> None:
    assert sha256_bytes(b"") == hashlib.sha256(b"").hexdigest()


@pytest.mark.unit
def test_sha256_bytes_known_value() -> None:
    assert sha256_bytes(b"hello") == hashlib.sha256(b"hello").hexdigest()


@pytest.mark.unit
def test_sha256_streaming_empty() -> None:
    assert sha256_stream(io.BytesIO(b"")) == hashlib.sha256(b"").hexdigest()


@pytest.mark.unit
def test_sha256_streaming_1mb() -> None:
    payload = b"x" * (1024 * 1024)
    assert sha256_stream(io.BytesIO(payload)) == hashlib.sha256(payload).hexdigest()


@pytest.mark.unit
def test_sha256_streaming_20mb() -> None:
    payload = b"y" * (20 * 1024 * 1024)
    assert sha256_stream(io.BytesIO(payload)) == hashlib.sha256(payload).hexdigest()


@pytest.mark.unit
def test_sha256_streaming_chunk_boundary() -> None:
    # Contenu de taille non multiple du chunk pour vérifier la fin du flux.
    payload = b"abc" * 50001
    assert sha256_stream(io.BytesIO(payload)) == hashlib.sha256(payload).hexdigest()


@pytest.mark.unit
def test_is_valid_sha256_hex_ok() -> None:
    valid = "a" * 64
    assert is_valid_sha256_hex(valid) is True
    assert is_valid_sha256_hex(hashlib.sha256(b"").hexdigest()) is True


@pytest.mark.unit
def test_is_valid_sha256_hex_rejects_bad_inputs() -> None:
    assert is_valid_sha256_hex("") is False
    assert is_valid_sha256_hex("a" * 63) is False
    assert is_valid_sha256_hex("z" * 64) is False
    assert is_valid_sha256_hex(None) is False  # type: ignore[arg-type]
