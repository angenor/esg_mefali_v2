"""F22 - Tests unit OcrService (PDF natif + dispatcher mime).

Tests autonomes (pas de DB). Utilisent un PDF minimal hand-crafted.
"""

from __future__ import annotations

import pytest

from app.services.ocr_service import (
    OcrOutcome,
    extract_text,
    extract_text_from_pdf,
)

# PDF minimal valide avec texte "Hello F22 statuts".
PDF_WITH_TEXT = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 55>>stream\n"
    b"BT\n/F1 18 Tf\n72 720 Td\n(Hello F22 statuts) Tj\nET\n"
    b"endstream\nendobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000055 00000 n \n0000000101 00000 n \n0000000196 00000 n \n"
    b"0000000294 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n349\n%%EOF"
)


# PDF minimal sans aucun texte (page vide).
PDF_EMPTY = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000055 00000 n \n0000000101 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n156\n%%EOF"
)


class TestExtractTextFromPdf:
    def test_extract_pdf_with_native_text_returns_text(self) -> None:
        text = extract_text_from_pdf(PDF_WITH_TEXT)
        assert "Hello F22 statuts" in text

    def test_extract_pdf_without_text_returns_empty(self) -> None:
        text = extract_text_from_pdf(PDF_EMPTY)
        assert text == ""

    def test_extract_pdf_corrupt_raises(self) -> None:
        with pytest.raises(Exception):  # noqa: B017 — pypdf raises various types
            extract_text_from_pdf(b"not a pdf at all")

    def test_extract_timeout_raises_timeout_error(self, monkeypatch) -> None:
        # On simule un parsing lent en patchant la fonction synchrone
        # pour qu'elle dorme au-dela du timeout.
        import time

        from app.services import ocr_service

        def slow_read(_data: bytes) -> str:
            time.sleep(2.0)
            return "should not reach here"

        monkeypatch.setattr(ocr_service, "_read_pdf_text_sync", slow_read)
        with pytest.raises(TimeoutError):
            extract_text_from_pdf(PDF_WITH_TEXT, timeout_s=0.05)


class TestExtractTextDispatcher:
    def test_pdf_with_text_returns_done(self) -> None:
        out = extract_text("application/pdf", PDF_WITH_TEXT)
        assert isinstance(out, OcrOutcome)
        assert out.status == "done"
        assert out.text and "Hello F22 statuts" in out.text
        assert out.error is None

    def test_pdf_empty_returns_deferred(self) -> None:
        out = extract_text("application/pdf", PDF_EMPTY)
        assert out.status == "deferred"
        assert out.text is None
        assert out.error == "pdf_no_native_text"

    def test_pdf_corrupt_returns_failed(self) -> None:
        out = extract_text("application/pdf", b"not a pdf")
        assert out.status == "failed"
        assert out.text is None
        assert out.error and out.error.startswith("pdf_extract_error:")

    def test_pdf_timeout_returns_failed(self, monkeypatch) -> None:
        import time

        from app.services import ocr_service

        def slow_read(_data: bytes) -> str:
            time.sleep(2.0)
            return "x"

        monkeypatch.setattr(ocr_service, "_read_pdf_text_sync", slow_read)
        out = extract_text("application/pdf", PDF_WITH_TEXT, timeout_s=0.05)
        assert out.status == "failed"
        assert out.error and "timeout" in out.error.lower()

    @pytest.mark.parametrize("mime", ["image/jpeg", "image/png", "image/heic"])
    def test_image_returns_deferred(self, mime: str) -> None:
        out = extract_text(mime, b"\xff\xd8\xff\xe0")
        assert out.status == "deferred"
        assert out.error == "mvp_image_unsupported"

    @pytest.mark.parametrize(
        "mime",
        [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ],
    )
    def test_office_returns_deferred(self, mime: str) -> None:
        out = extract_text(mime, b"PK\x03\x04")
        assert out.status == "deferred"
        assert out.error == "mvp_office_unsupported"

    def test_unknown_mime_returns_failed(self) -> None:
        out = extract_text("application/x-unknown", b"abc")
        assert out.status == "failed"
        assert out.error and "mime_not_supported" in out.error
