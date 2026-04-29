"""F12 - Validators dedies (indicateurs, mime, size)."""

from __future__ import annotations

from typing import Any

# Whitelist mime upload documents projet.
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
    "image/webp",
})

MAX_DOC_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
MAX_DOCS_PER_PROJET: int = 50

ALLOWED_DOC_TYPES: frozenset[str] = frozenset({
    "faisabilite", "business_plan", "etude_impact",
    "lettre_soutien", "photo", "autre",
})

ALLOWED_TYPES_IMPACT: frozenset[str] = frozenset({
    "mitigation_carbone", "adaptation", "biodiversite",
    "economie_circulaire", "eau", "energies_renouvelables",
    "agriculture_durable", "foret_sols", "autre",
})

ALLOWED_STRUCTURES_FINANCEMENT: frozenset[str] = frozenset({
    "subvention", "pret_concessionnel", "equity", "blending",
})

ALLOWED_STATUTS: tuple[str, ...] = (
    "brouillon", "en_recherche_financement", "finance",
    "en_execution", "cloture",
)

ALLOWED_MATURITES: tuple[str, ...] = (
    "ideation", "pre_faisabilite", "pilote", "scale", "replication",
)


class ValidationError(ValueError):
    """Erreur de validation metier (cf. F12)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_indicateurs(arr: Any) -> list[dict[str, Any]]:
    """Valide indicateurs_impact_json: liste d'objets {key, value, unit}.

    - key: str non vide.
    - value: int|float (numerique).
    - unit: str non vide.
    """
    if arr is None:
        return []
    if not isinstance(arr, list):
        raise ValidationError(
            "indicateurs_invalid",
            "indicateurs_impact doit etre une liste",
        )
    out: list[dict[str, Any]] = []
    for i, item in enumerate(arr):
        if not isinstance(item, dict):
            raise ValidationError(
                "indicateurs_invalid_item",
                f"indicateurs_impact[{i}] doit etre un objet",
            )
        key = item.get("key")
        value = item.get("value")
        unit = item.get("unit")
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(
                "indicateurs_invalid_key",
                f"indicateurs_impact[{i}].key doit etre une chaine non vide",
            )
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValidationError(
                "indicateurs_invalid_value",
                f"indicateurs_impact[{i}].value doit etre numerique",
            )
        if not isinstance(unit, str) or not unit.strip():
            raise ValidationError(
                "indicateurs_invalid_unit",
                f"indicateurs_impact[{i}].unit doit etre une chaine non vide",
            )
        out.append({"key": key.strip(), "value": value, "unit": unit.strip()})
    return out


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
    if size > MAX_DOC_SIZE_BYTES:
        raise ValidationError(
            "size_too_large",
            f"Taille > {MAX_DOC_SIZE_BYTES} octets (25 MB)",
        )
    return size


def validate_doc_type(doc_type: str) -> str:
    if doc_type not in ALLOWED_DOC_TYPES:
        raise ValidationError(
            "doc_type_invalid",
            f"Type document invalide: {doc_type}",
        )
    return doc_type


def validate_types_impact(arr: list[str] | None) -> list[str] | None:
    if arr is None:
        return None
    if not isinstance(arr, list):
        raise ValidationError("types_impact_invalid", "types_impact doit etre une liste")
    for v in arr:
        if v not in ALLOWED_TYPES_IMPACT:
            raise ValidationError(
                "types_impact_invalid_value",
                f"types_impact[]: {v} non autorise",
            )
    return list(arr)


def validate_structure_financement(arr: list[str] | None) -> list[str] | None:
    if arr is None:
        return None
    if not isinstance(arr, list):
        raise ValidationError("structure_invalid", "structure_financement doit etre une liste")
    for v in arr:
        if v not in ALLOWED_STRUCTURES_FINANCEMENT:
            raise ValidationError(
                "structure_invalid_value",
                f"structure_financement[]: {v} non autorise",
            )
    return list(arr)


def validate_statut(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in ALLOWED_STATUTS:
        raise ValidationError("statut_invalid", f"statut invalide: {value}")
    return value


def validate_maturite(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in ALLOWED_MATURITES:
        raise ValidationError("maturite_invalid", f"maturite invalide: {value}")
    return value
