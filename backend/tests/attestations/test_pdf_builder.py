"""F30 - Smoke tests pour la generation PDF."""

from __future__ import annotations

from app.attestations.pdf_builder import _truncate, render_attestation_pdf


def test_render_attestation_pdf_returns_pdf_bytes() -> None:
    pdf = render_attestation_pdf(
        entreprise_name="ACME",
        public_id="00000000-0000-0000-0000-000000000001",
        generated_at_iso="2026-04-29T10:00:00+00:00",
        valid_until_iso="2026-10-29T10:00:00+00:00",
        scores={"solvability": {"score": 72}},
        referentiels_versions={"esg_uemoa_pme_v1": "2025-09"},
        verify_url="https://example.test/verify/00000000-0000-0000-0000-000000000001",
        signature_hex="ab" * 32,
        pubkey_fingerprint="ef" * 32,
    )
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1500  # smoke: at least a kB


def test_render_attestation_pdf_handles_empty_scores() -> None:
    pdf = render_attestation_pdf(
        entreprise_name="ACME",
        public_id="00000000-0000-0000-0000-000000000002",
        generated_at_iso="2026-04-29T10:00:00+00:00",
        valid_until_iso="2026-10-29T10:00:00+00:00",
        scores={},
        referentiels_versions={},
        verify_url="https://example.test/verify/x",
        signature_hex="ab" * 32,
        pubkey_fingerprint="ef" * 32,
    )
    assert pdf.startswith(b"%PDF-")


def test_truncate_short_value_kept_as_is() -> None:
    assert _truncate("short") == "short"


def test_truncate_long_value_collapsed() -> None:
    long = "abcdefghijklmnopqrstuvwxyz"
    out = _truncate(long, head=4, tail=4)
    assert out == "abcd...wxyz"
