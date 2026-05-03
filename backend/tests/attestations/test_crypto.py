"""F30 - Tests unitaires pour app.attestations.crypto."""

from __future__ import annotations

import hashlib
import json
import os

import pytest

from app.attestations import crypto


@pytest.fixture()
def keypair(monkeypatch: pytest.MonkeyPatch) -> crypto.KeyPair:
    seed_hex = os.urandom(32).hex()
    monkeypatch.setenv("ATTESTATION_PRIVATE_KEY_HEX", seed_hex)
    return crypto.load_keypair()


def test_canonicalize_is_deterministic_and_sorted() -> None:
    a = crypto.canonicalize_document({"b": 2, "a": 1})
    b = crypto.canonicalize_document({"a": 1, "b": 2})
    assert a == b
    assert a == b'{"a":1,"b":2}'


def test_canonicalize_preserves_unicode() -> None:
    payload = crypto.canonicalize_document({"name": "Côte d'Ivoire"})
    assert payload == '{"name":"Côte d\'Ivoire"}'.encode()


def test_compute_document_hash_matches_sha256() -> None:
    payload = crypto.canonicalize_document({"k": 1})
    expected = hashlib.sha256(payload).hexdigest()
    assert crypto.compute_document_hash(payload) == expected


def test_load_keypair_raises_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATTESTATION_PRIVATE_KEY_HEX", raising=False)
    with pytest.raises(crypto.KeyNotConfiguredError):
        crypto.load_keypair()


def test_load_keypair_raises_when_env_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTESTATION_PRIVATE_KEY_HEX", "not-hex")
    with pytest.raises(crypto.KeyNotConfiguredError):
        crypto.load_keypair()


def test_load_keypair_raises_when_wrong_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTESTATION_PRIVATE_KEY_HEX", "ab" * 16)  # 16 bytes
    with pytest.raises(crypto.KeyNotConfiguredError):
        crypto.load_keypair()


def test_sign_then_verify_roundtrip(keypair: crypto.KeyPair) -> None:
    payload = crypto.canonicalize_document({"a": 1, "b": [1, 2], "c": {"d": "e"}})
    sig = crypto.sign_document(payload, keypair)
    assert crypto.verify_signature(payload, sig, keypair.public_hex) is True


def test_verify_rejects_tampered_payload(keypair: crypto.KeyPair) -> None:
    payload = crypto.canonicalize_document({"a": 1})
    sig = crypto.sign_document(payload, keypair)
    tampered = crypto.canonicalize_document({"a": 2})
    assert crypto.verify_signature(tampered, sig, keypair.public_hex) is False


def test_verify_rejects_bad_signature_format(keypair: crypto.KeyPair) -> None:
    payload = crypto.canonicalize_document({"a": 1})
    assert crypto.verify_signature(payload, "not-hex", keypair.public_hex) is False
    assert crypto.verify_signature(payload, "ab" * 32, keypair.public_hex) is False


def test_verify_rejects_bad_pubkey_length(keypair: crypto.KeyPair) -> None:
    payload = crypto.canonicalize_document({"a": 1})
    sig = crypto.sign_document(payload, keypair)
    assert crypto.verify_signature(payload, sig, "ab" * 16) is False


def test_fingerprint_matches_sha256_of_pubkey(keypair: crypto.KeyPair) -> None:
    pub_bytes = bytes.fromhex(keypair.public_hex)
    assert keypair.fingerprint == hashlib.sha256(pub_bytes).hexdigest()


def test_canonical_document_is_reproducible_externally(
    keypair: crypto.KeyPair,
) -> None:
    """A naive third-party client can rebuild the same payload bytes."""
    doc = {
        "entreprise_name": "ACME",
        "generated_at": "2026-04-29T10:00:00+00:00",
        "public_id": "00000000-0000-0000-0000-000000000001",
        "referentiels_versions": {"esg_uemoa_pme_v1": "2025-09"},
        "schema_version": "v1",
        "scores": {"solvability": {"score": 72}},
        "valid_until": "2026-10-29T10:00:00+00:00",
    }
    canonical = crypto.canonicalize_document(doc)
    naive = json.dumps(
        doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert canonical == naive
    sig = crypto.sign_document(canonical, keypair)
    assert crypto.verify_signature(canonical, sig, keypair.public_hex) is True
