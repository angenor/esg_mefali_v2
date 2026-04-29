"""F30 - Tests AttestationService.generate avec mocks (sans DB)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from app.attestations import crypto
from app.attestations.service import (
    AttestationService,
    GenerateInput,
    KeyMissingError,
    ScoresUnavailableError,
)
from app.storage.local import LocalStorage


class _FakeSession:
    """Stub minimal de SQLAlchemy Session utilise par AttestationService."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed += 1


@pytest.fixture()
def keypair_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTESTATION_PRIVATE_KEY_HEX", os.urandom(32).hex())


@pytest.fixture()
def fake_storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path)


@pytest.fixture()
def service(
    keypair_env: None,
    fake_storage: LocalStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> AttestationService:
    import app.attestations.service as svc_mod

    monkeypatch.setattr(svc_mod, "record_audit", lambda *a, **kw: None)
    db = _FakeSession()
    return AttestationService(
        db=db,  # type: ignore[arg-type]
        storage=fake_storage,
        app_url="https://example.test",
    )


def test_generate_persists_signed_attestation_and_pdf(
    service: AttestationService,
) -> None:
    payload = GenerateInput(
        account_id=uuid.uuid4(),
        entreprise_id=uuid.uuid4(),
        entreprise_name="ACME",
        generated_by=uuid.uuid4(),
        scores_to_include=["solvability"],
        valid_for_months=6,
        scores_resolved={"solvability": {"score": 72}},
        referentiels_versions={"esg_uemoa_pme_v1": "2025-09"},
    )
    row = service.generate(payload)

    assert row.signature_ed25519
    assert len(row.signature_ed25519) == 128
    assert len(row.hash_document) == 64

    pdf_bytes = service.storage.read(row.file_path)
    assert pdf_bytes.startswith(b"%PDF-")

    keypair = crypto.load_keypair()
    assert keypair.fingerprint == row.pubkey_fingerprint

    document = {
        "entreprise_name": "ACME",
        "generated_at": row.generated_at.isoformat(),
        "public_id": str(row.public_id),
        "referentiels_versions": {"esg_uemoa_pme_v1": "2025-09"},
        "schema_version": "v1",
        "scores": row.scores_inclus_json,
        "valid_until": row.valid_until.isoformat(),
    }
    canonical = crypto.canonicalize_document(document)
    assert (
        crypto.verify_signature(canonical, row.signature_ed25519, keypair.public_hex)
        is True
    )


def test_generate_rejects_missing_scores(service: AttestationService) -> None:
    payload = GenerateInput(
        account_id=uuid.uuid4(),
        entreprise_id=uuid.uuid4(),
        entreprise_name="ACME",
        generated_by=uuid.uuid4(),
        scores_to_include=["solvability"],
        valid_for_months=6,
        scores_resolved={},
        referentiels_versions={},
    )
    with pytest.raises(ScoresUnavailableError):
        service.generate(payload)


def test_generate_rejects_invalid_valid_for_months(
    service: AttestationService,
) -> None:
    payload = GenerateInput(
        account_id=uuid.uuid4(),
        entreprise_id=uuid.uuid4(),
        entreprise_name="ACME",
        generated_by=uuid.uuid4(),
        scores_to_include=["solvability"],
        valid_for_months=4,
        scores_resolved={"solvability": {"score": 72}},
        referentiels_versions={},
    )
    with pytest.raises(ValueError):
        service.generate(payload)


def test_generate_raises_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
    fake_storage: LocalStorage,
) -> None:
    monkeypatch.delenv("ATTESTATION_PRIVATE_KEY_HEX", raising=False)
    import app.attestations.service as svc_mod

    monkeypatch.setattr(svc_mod, "record_audit", lambda *a, **kw: None)
    service = AttestationService(
        db=_FakeSession(),  # type: ignore[arg-type]
        storage=fake_storage,
        app_url="https://example.test",
    )
    payload = GenerateInput(
        account_id=uuid.uuid4(),
        entreprise_id=uuid.uuid4(),
        entreprise_name="ACME",
        generated_by=uuid.uuid4(),
        scores_to_include=["solvability"],
        valid_for_months=6,
        scores_resolved={"solvability": {"score": 72}},
        referentiels_versions={},
    )
    with pytest.raises(KeyMissingError):
        service.generate(payload)
