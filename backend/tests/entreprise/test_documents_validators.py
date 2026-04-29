"""F22 - Tests unit documents_validators (mime / size / doc_type)."""

from __future__ import annotations

import pytest

from app.entreprise.documents_validators import (
    ALLOWED_DOC_TYPES,
    ALLOWED_MIME_TYPES,
    MAX_DOCS_PER_ENTREPRISE,
    MAX_FILE_BYTES,
    ValidationError,
    validate_doc_type,
    validate_mime,
    validate_size,
)


class TestConstants:
    def test_max_docs_is_50(self) -> None:
        assert MAX_DOCS_PER_ENTREPRISE == 50

    def test_max_size_is_25_mb(self) -> None:
        assert MAX_FILE_BYTES == 25 * 1024 * 1024

    def test_pdf_in_whitelist(self) -> None:
        assert "application/pdf" in ALLOWED_MIME_TYPES

    def test_heic_in_whitelist(self) -> None:
        assert "image/heic" in ALLOWED_MIME_TYPES

    def test_docx_xlsx_in_whitelist(self) -> None:
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in ALLOWED_MIME_TYPES
        )
        assert (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            in ALLOWED_MIME_TYPES
        )

    def test_doc_types_complete(self) -> None:
        assert ALLOWED_DOC_TYPES == frozenset(
            {"statuts", "rapport_activite", "facture", "contrat", "politique", "autre"}
        )


class TestValidateMime:
    def test_pdf_ok(self) -> None:
        assert validate_mime("application/pdf") == "application/pdf"

    def test_exe_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_mime("application/x-msdownload")
        assert exc_info.value.code == "mime_not_allowed"

    def test_svg_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_mime("image/svg+xml")
        assert exc_info.value.code == "mime_not_allowed"


class TestValidateSize:
    def test_size_within_limit(self) -> None:
        assert validate_size(1024) == 1024

    def test_size_zero_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_size(0)
        assert exc_info.value.code == "size_invalid"

    def test_size_negative_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_size(-1)
        assert exc_info.value.code == "size_invalid"

    def test_size_too_large_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_size(MAX_FILE_BYTES + 1)
        assert exc_info.value.code == "size_too_large"

    def test_size_at_limit_ok(self) -> None:
        assert validate_size(MAX_FILE_BYTES) == MAX_FILE_BYTES


class TestValidateDocType:
    def test_statuts_ok(self) -> None:
        assert validate_doc_type("statuts") == "statuts"

    @pytest.mark.parametrize(
        "dt", ["rapport_activite", "facture", "contrat", "politique", "autre"]
    )
    def test_all_allowed_types_ok(self, dt: str) -> None:
        assert validate_doc_type(dt) == dt

    def test_unknown_type_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_doc_type("inconnu")
        assert exc_info.value.code == "doc_type_invalid"
