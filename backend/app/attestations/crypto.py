"""F30 - Cryptographie attestation verifiable.

Pure functions for canonical JSON, sha256 hash, Ed25519 sign / verify.

The private key is loaded lazily from the environment variable
``ATTESTATION_PRIVATE_KEY_HEX`` (32 bytes hex = 64 chars). Absence triggers
``KeyNotConfiguredError`` so callers can return HTTP 503 cleanly.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class KeyNotConfiguredError(RuntimeError):
    """Raised when the Ed25519 private key is not configured."""


_ENV_VAR = "ATTESTATION_PRIVATE_KEY_HEX"


@dataclass(frozen=True)
class KeyPair:
    """Holds the loaded Ed25519 keypair plus its fingerprint."""

    private: Ed25519PrivateKey
    public: Ed25519PublicKey
    public_hex: str
    fingerprint: str

    def sign(self, payload: bytes) -> str:
        """Sign ``payload`` and return the signature as lowercase hex."""
        return self.private.sign(payload).hex()


def _load_seed_from_env(env: dict[str, str] | None = None) -> bytes:
    src = env if env is not None else os.environ
    raw = src.get(_ENV_VAR, "").strip()
    if not raw:
        raise KeyNotConfiguredError(
            f"{_ENV_VAR} is not set. Run "
            "`python -m app.scripts.generate_attestation_keys` to mint one."
        )
    try:
        seed = bytes.fromhex(raw)
    except ValueError as exc:
        raise KeyNotConfiguredError(
            f"{_ENV_VAR} must be a hex string (32 bytes = 64 chars)."
        ) from exc
    if len(seed) != 32:
        raise KeyNotConfiguredError(
            f"{_ENV_VAR} must be exactly 32 bytes; got {len(seed)}."
        )
    return seed


def load_keypair(env: dict[str, str] | None = None) -> KeyPair:
    """Load the Ed25519 keypair from the environment.

    Caller is responsible for caching the result if desired; the function
    itself does not memoize, which keeps tests deterministic.
    """
    seed = _load_seed_from_env(env)
    private = Ed25519PrivateKey.from_private_bytes(seed)
    public = private.public_key()
    public_bytes = public.public_bytes_raw()
    public_hex = public_bytes.hex()
    fingerprint = hashlib.sha256(public_bytes).hexdigest()
    return KeyPair(
        private=private,
        public=public,
        public_hex=public_hex,
        fingerprint=fingerprint,
    )


def canonicalize_document(document: dict[str, Any]) -> bytes:
    """Return the canonical UTF-8 byte representation of ``document``.

    Keys are sorted lexicographically, no extra whitespace, ``ensure_ascii``
    is disabled so unicode is preserved. This makes it trivial to reproduce
    the same bytes from Node.js or Python without any extra lib.
    """
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def compute_document_hash(payload: bytes) -> str:
    """Return the lowercase hex sha256 of ``payload``."""
    return hashlib.sha256(payload).hexdigest()


def sign_document(payload: bytes, keypair: KeyPair) -> str:
    """Sign ``payload`` and return the signature as lowercase hex."""
    return keypair.sign(payload)


def verify_signature(payload: bytes, signature_hex: str, public_hex: str) -> bool:
    """Return True when the Ed25519 signature is valid for ``payload``.

    Returns False on any failure (malformed hex, wrong length, bad sig).
    Never raises on bad input - callers can branch directly on the bool.
    """
    try:
        signature = bytes.fromhex(signature_hex)
        public_bytes = bytes.fromhex(public_hex)
    except ValueError:
        return False
    if len(public_bytes) != 32 or len(signature) != 64:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, payload)
        return True
    except InvalidSignature:
        return False
