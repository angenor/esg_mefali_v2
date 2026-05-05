"""F50 (T018) — tests unitaires validators upload (size + MIME).

Valide :
- ``validate_size`` rejette > 25 Mo avec ``size_too_large`` (HTTP 413).
- ``validate_mime`` rejette les MIME hors whitelist avec ``mime_not_allowed`` (HTTP 415).
- ``validate_mime`` accepte tous les MIME du whitelist F22 (PDF/JPG/PNG/HEIC/DOCX/XLSX).
- ``validate_size`` rejette les valeurs <= 0 avec ``size_invalid``.

Tests pure-Python sans DB ; pas de fixture nécessaire au-delà du runner.
"""

from __future__ import annotations

import pytest

from app.entreprise.documents_validators import (
    ALLOWED_DOC_TYPES,
    ALLOWED_MIME_TYPES,
    MAX_FILE_BYTES,
    ValidationError,
    validate_doc_type,
    validate_mime,
    validate_size,
)


@pytest.mark.unit
class TestValidateSize:
    def test_zero_byte_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_size(0)
        assert exc.value.code == "size_invalid"

    def test_negative_size_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_size(-1)
        assert exc.value.code == "size_invalid"

    def test_non_int_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_size("100")  # type: ignore[arg-type]
        assert exc.value.code == "size_invalid"

    def test_within_limit_accepted(self) -> None:
        # 1 octet, 1 Ko, 1 Mo, 25 Mo : tous valides.
        for size in (1, 1024, 1_000_000, MAX_FILE_BYTES):
            assert validate_size(size) == size

    def test_exceeds_max_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_size(MAX_FILE_BYTES + 1)
        assert exc.value.code == "size_too_large"
        assert "25" in exc.value.message  # mentionne la limite humanisée

    def test_max_file_bytes_is_25mb(self) -> None:
        # FR-002 — limite par fichier.
        assert MAX_FILE_BYTES == 25 * 1024 * 1024


@pytest.mark.unit
class TestValidateMime:
    @pytest.mark.parametrize(
        "mime",
        [
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/heic",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
        ],
    )
    def test_allowed_mimes_accepted(self, mime: str) -> None:
        assert validate_mime(mime) == mime

    @pytest.mark.parametrize(
        "mime",
        [
            "application/x-msdownload",  # .exe
            "application/zip",
            "text/html",
            "application/javascript",
            "application/octet-stream",
            "image/gif",
            "image/svg+xml",
            "",
        ],
    )
    def test_disallowed_mimes_rejected(self, mime: str) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_mime(mime)
        assert exc.value.code == "mime_not_allowed"

    def test_whitelist_is_immutable_frozenset(self) -> None:
        # FR-003 — la whitelist doit être immutable au runtime.
        assert isinstance(ALLOWED_MIME_TYPES, frozenset)
        assert len(ALLOWED_MIME_TYPES) == 6


@pytest.mark.unit
class TestValidateDocType:
    def test_known_types_accepted(self) -> None:
        for t in ALLOWED_DOC_TYPES:
            assert validate_doc_type(t) == t

    def test_unknown_type_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_doc_type("inconnu")
        assert exc.value.code == "doc_type_invalid"

    def test_canonical_types_present(self) -> None:
        # FR-001 — types métier autorisés F22.
        assert {"statuts", "rapport_activite", "facture", "contrat", "politique", "autre"} <= ALLOWED_DOC_TYPES


@pytest.mark.unit
class TestValidationErrorContract:
    """L'exception expose ``code`` et ``message`` pour le mapping HTTP."""

    def test_error_carries_code_and_message(self) -> None:
        err = ValidationError("size_too_large", "X")
        assert err.code == "size_too_large"
        assert err.message == "X"
        assert str(err) == "X"

    def test_size_too_large_maps_to_413(self) -> None:
        # Reproduit le mapping fait dans entreprise_documents.py upload_endpoint.
        try:
            validate_size(MAX_FILE_BYTES + 1)
        except ValidationError as exc:
            assert exc.code == "size_too_large"  # → 413
        else:
            pytest.fail("validate_size aurait dû lever")

    def test_mime_not_allowed_maps_to_415(self) -> None:
        try:
            validate_mime("application/x-evil")
        except ValidationError as exc:
            assert exc.code == "mime_not_allowed"  # → 415
        else:
            pytest.fail("validate_mime aurait dû lever")
