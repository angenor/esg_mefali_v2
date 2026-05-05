"""F22 - Validators dedies aux documents entreprise (mime/size/type).

Calque le module ``app/projets/validators.py`` (F12) en restreignant la
whitelist mime aux types F22 (PDF, JPG, PNG, HEIC, DOCX, XLSX) et le
type metier aux documents juridiques/administratifs entreprise.
"""

from __future__ import annotations

# Whitelist mime upload documents entreprise (FR-003).
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/heic",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
})

# Limite par fichier : 25 MB (FR-002).
MAX_FILE_BYTES: int = 25 * 1024 * 1024

# Cap par entreprise (FR-004 — élevé F50 50 → 200).
MAX_DOCS_PER_ENTREPRISE: int = 200

# Délai (jours) avant purge dure d'un document soft-deleted (F50 Q2).
DOCUMENT_PURGE_DAYS: int = 30

# Types metier autorises (FR-001).
ALLOWED_DOC_TYPES: frozenset[str] = frozenset({
    "statuts",
    "rapport_activite",
    "facture",
    "contrat",
    "politique",
    "autre",
})


class ValidationError(ValueError):
    """Erreur de validation metier (calque F12)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_mime(mime: str) -> str:
    if mime not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            "mime_not_allowed",
            f"Mime type non autorise: {mime}",
        )
    return mime


def validate_size(size: int) -> int:
    if not isinstance(size, int) or size <= 0:
        raise ValidationError("size_invalid", "Taille fichier invalide")
    if size > MAX_FILE_BYTES:
        raise ValidationError(
            "size_too_large",
            f"Taille > {MAX_FILE_BYTES} octets (25 MB)",
        )
    return size


def validate_doc_type(doc_type: str) -> str:
    if doc_type not in ALLOWED_DOC_TYPES:
        raise ValidationError(
            "doc_type_invalid",
            f"Type document invalide: {doc_type}",
        )
    return doc_type
