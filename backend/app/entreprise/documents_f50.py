"""F50 — Extensions du service documents (fingerprint, validation, M:N projet).

Module séparé pour ne pas alourdir ``documents_service.py`` (F22) et faciliter
les tests. Les fonctions opèrent sur la même table ``document_entreprise`` et
sur la nouvelle table ``document_link_projet``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.entreprise.documents_service import (
    DocumentEntrepriseRow,
    DocumentNotFound,
    _row_to_dataclass,
)
from app.entreprise.documents_validators import DOCUMENT_PURGE_DAYS


@dataclass(frozen=True)
class DocumentF50Extras:
    content_sha256_hex: str | None
    extraction_payload: dict[str, Any]
    extraction_validated_at: datetime | None
    extraction_validated_by: UUID | None
    purge_scheduled_at: datetime | None
    linked_projets: tuple[UUID, ...]
    tags: tuple[str, ...]


_DOC_F50_COLS = (
    "id, account_id, entreprise_id, name, original_filename, mime_type, "
    "size_bytes, type, storage_path, text_content, ocr_status, ocr_error, "
    "uploaded_by, created_at, "
    "encode(content_sha256, 'hex') AS content_sha256_hex, "
    "extraction_payload, extraction_validated_at, extraction_validated_by, "
    "purge_scheduled_at"
)


def _fetch_extras(db: Session, doc_id: UUID | str) -> DocumentF50Extras | None:
    row = db.execute(
        text(
            "SELECT encode(content_sha256, 'hex') AS sha_hex, extraction_payload, "
            "extraction_validated_at, extraction_validated_by, purge_scheduled_at, "
            "COALESCE(tags, ARRAY[]::TEXT[]) AS tags "
            "FROM document_entreprise WHERE id = CAST(:id AS UUID)"
        ),
        {"id": str(doc_id)},
    ).first()
    if row is None:
        return None
    links = db.execute(
        text(
            "SELECT projet_id FROM document_link_projet "
            "WHERE document_id = CAST(:id AS UUID)"
        ),
        {"id": str(doc_id)},
    ).all()
    payload = row.extraction_payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            payload = {}
    return DocumentF50Extras(
        content_sha256_hex=row.sha_hex,
        extraction_payload=payload or {},
        extraction_validated_at=row.extraction_validated_at,
        extraction_validated_by=row.extraction_validated_by,
        purge_scheduled_at=row.purge_scheduled_at,
        linked_projets=tuple(r.projet_id for r in links),
        tags=tuple(row.tags or ()),
    )


def serialize_document(row: DocumentEntrepriseRow, extras: DocumentF50Extras | None) -> dict[str, Any]:
    """Sérialise un DocumentEntrepriseRow + extras F50 vers la forme contractuelle."""
    e = extras or DocumentF50Extras(
        content_sha256_hex=None,
        extraction_payload={},
        extraction_validated_at=None,
        extraction_validated_by=None,
        purge_scheduled_at=None,
        linked_projets=(),
        tags=(),
    )
    return {
        "id": str(row.id),
        "entreprise_id": str(row.entreprise_id),
        "name": row.name,
        "original_filename": row.original_filename,
        "mime_type": row.mime_type,
        "size_bytes": row.size_bytes,
        "type": row.type,
        "ocr_status": row.ocr_status,
        "ocr_error": row.ocr_error,
        "uploaded_by": str(row.uploaded_by) if row.uploaded_by else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "content_sha256": e.content_sha256_hex,
        "extraction_payload": e.extraction_payload or {},
        "extraction_validated_at": (
            e.extraction_validated_at.isoformat()
            if e.extraction_validated_at
            else None
        ),
        "extraction_validated_by": (
            str(e.extraction_validated_by) if e.extraction_validated_by else None
        ),
        "linked_projets": [str(p) for p in e.linked_projets],
        "tags": list(e.tags),
        "deleted_at": None,
        "purge_scheduled_at": (
            e.purge_scheduled_at.isoformat() if e.purge_scheduled_at else None
        ),
    }


# ---------------------------------------------------------------------------
# Fingerprint dedup
# ---------------------------------------------------------------------------


def find_by_fingerprint(
    db: Session, *, account_id: UUID | str, sha256_hex: str
) -> DocumentEntrepriseRow | None:
    """Cherche un document non supprimé du compte courant portant cette empreinte."""
    row = db.execute(
        text(
            f"SELECT {_DOC_F50_COLS} FROM document_entreprise "
            "WHERE account_id = CAST(:aid AS UUID) "
            "AND deleted_at IS NULL "
            "AND content_sha256 = decode(:sha, 'hex') "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"aid": str(account_id), "sha": sha256_hex},
    ).first()
    return _row_to_dataclass(row) if row is not None else None


def store_fingerprint(
    db: Session, *, doc_id: UUID | str, sha256_hex: str
) -> None:
    db.execute(
        text(
            "UPDATE document_entreprise SET content_sha256 = decode(:sha, 'hex') "
            "WHERE id = CAST(:id AS UUID)"
        ),
        {"sha": sha256_hex, "id": str(doc_id)},
    )


# ---------------------------------------------------------------------------
# Liens projet (M:N — Q1)
# ---------------------------------------------------------------------------


class ProjetNotFound(Exception):
    pass


class CrossAccountProjet(Exception):
    pass


def _projet_account_id(db: Session, projet_id: UUID | str) -> UUID | None:
    row = db.execute(
        text("SELECT account_id FROM projet WHERE id = CAST(:pid AS UUID)"),
        {"pid": str(projet_id)},
    ).first()
    return row.account_id if row else None


def link_document_to_projet(
    db: Session,
    *,
    account_id: UUID | str,
    doc_id: UUID | str,
    projet_id: UUID | str,
    user_id: UUID | str,
) -> bool:
    """Crée un lien document_entreprise ↔ projet ; idempotent.

    Retourne ``True`` si la ligne a été créée, ``False`` si déjà existante.
    """
    pacc = _projet_account_id(db, projet_id)
    if pacc is None:
        raise ProjetNotFound()
    if str(pacc) != str(account_id):
        raise CrossAccountProjet()

    existing = db.execute(
        text(
            "SELECT 1 FROM document_link_projet "
            "WHERE document_id = CAST(:did AS UUID) AND projet_id = CAST(:pid AS UUID)"
        ),
        {"did": str(doc_id), "pid": str(projet_id)},
    ).first()
    if existing is not None:
        return False

    new_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO document_link_projet (id, account_id, document_id, projet_id, created_by) "
            "VALUES (CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:did AS UUID), "
            "CAST(:pid AS UUID), CAST(:uid AS UUID))"
        ),
        {
            "id": str(new_id),
            "aid": str(account_id),
            "did": str(doc_id),
            "pid": str(projet_id),
            "uid": str(user_id),
        },
    )
    record_audit(
        db,
        entity_type="document_link_projet",
        entity_id=new_id,
        field=None,
        old=None,
        new={"document_id": str(doc_id), "projet_id": str(projet_id)},
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
        notes="document_link_projet.created",
    )
    return True


def unlink_document_from_projet(
    db: Session,
    *,
    account_id: UUID | str,
    doc_id: UUID | str,
    projet_id: UUID | str,
    user_id: UUID | str,
) -> bool:
    """Supprime un lien ; idempotent."""
    row = db.execute(
        text(
            "SELECT id FROM document_link_projet "
            "WHERE document_id = CAST(:did AS UUID) AND projet_id = CAST(:pid AS UUID) "
            "AND account_id = CAST(:aid AS UUID)"
        ),
        {
            "did": str(doc_id),
            "pid": str(projet_id),
            "aid": str(account_id),
        },
    ).first()
    if row is None:
        return False
    db.execute(
        text("DELETE FROM document_link_projet WHERE id = :id"),
        {"id": str(row.id)},
    )
    record_audit(
        db,
        entity_type="document_link_projet",
        entity_id=row.id,
        field=None,
        old={"document_id": str(doc_id), "projet_id": str(projet_id)},
        new=None,
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
        notes="document_link_projet.deleted",
    )
    return True


# ---------------------------------------------------------------------------
# Validation extraction
# ---------------------------------------------------------------------------


class AlreadyValidated(Exception):
    pass


def validate_extraction(
    db: Session,
    *,
    account_id: UUID | str,
    doc_id: UUID | str,
    user_id: UUID | str,
    fields: list[dict[str, Any]],
    propagate_to: list[dict[str, Any]],
    invalidate_existing: bool = False,
) -> dict[str, Any]:
    """Valide les champs extraits, persiste le snapshot, audite, propage si demandé.

    `propagate_to` est appliqué en best-effort — la propagation effective vers
    l'`entreprise`/`projet` est branchée par le router (qui orchestre les services
    métier ad hoc). Ici on persiste le snapshot et on émet l'audit.
    """
    row = db.execute(
        text(
            "SELECT extraction_validated_at FROM document_entreprise "
            "WHERE id = CAST(:id AS UUID) AND account_id = CAST(:aid AS UUID) "
            "AND deleted_at IS NULL"
        ),
        {"id": str(doc_id), "aid": str(account_id)},
    ).first()
    if row is None:
        raise DocumentNotFound()
    if row.extraction_validated_at is not None and not invalidate_existing:
        raise AlreadyValidated()

    snapshot = {"fields": fields, "propagate_to": propagate_to}
    db.execute(
        text(
            "UPDATE document_entreprise SET "
            "extraction_validated_at = now(), "
            "extraction_validated_by = CAST(:uid AS UUID), "
            "extraction_validation_payload = CAST(:snap AS JSONB), "
            "updated_at = now() "
            "WHERE id = CAST(:id AS UUID)"
        ),
        {
            "uid": str(user_id),
            "snap": json.dumps(snapshot),
            "id": str(doc_id),
        },
    )
    record_audit(
        db,
        entity_type="document_entreprise",
        entity_id=doc_id if isinstance(doc_id, UUID) else UUID(str(doc_id)),
        field="extraction_validated_at",
        old=None,
        new={"fields": fields},
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
        notes="document_entreprise.validate_extraction",
    )

    out_validated_at = db.execute(
        text(
            "SELECT extraction_validated_at FROM document_entreprise "
            "WHERE id = CAST(:id AS UUID)"
        ),
        {"id": str(doc_id)},
    ).scalar_one()
    return {
        "id": str(doc_id),
        "extraction_validated_at": out_validated_at.isoformat()
        if out_validated_at
        else None,
        "extraction_validated_by": str(user_id),
        "propagated": [
            {"entity": p.get("entity"), "id": p.get("id"), "fields_updated": []}
            for p in propagate_to
        ],
    }


# ---------------------------------------------------------------------------
# Soft-delete avec purge_scheduled_at
# ---------------------------------------------------------------------------


def soft_delete_with_purge(
    db: Session,
    *,
    account_id: UUID | str,
    doc_id: UUID | str,
    user_id: UUID | str,
) -> None:
    row = db.execute(
        text(
            "SELECT id FROM document_entreprise "
            "WHERE id = CAST(:id AS UUID) AND account_id = CAST(:aid AS UUID) "
            "AND deleted_at IS NULL"
        ),
        {"id": str(doc_id), "aid": str(account_id)},
    ).first()
    if row is None:
        raise DocumentNotFound()
    db.execute(
        text(
            f"UPDATE document_entreprise SET "
            f"deleted_at = now(), "
            f"purge_scheduled_at = now() + interval '{DOCUMENT_PURGE_DAYS} days', "
            f"updated_at = now() "
            f"WHERE id = CAST(:id AS UUID)"
        ),
        {"id": str(doc_id)},
    )
    record_audit(
        db,
        entity_type="document_entreprise",
        entity_id=row.id,
        field="deleted_at",
        old=None,
        new={"purge_scheduled_at": "+30d"},
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
        notes="document_entreprise.soft_delete",
    )


# ---------------------------------------------------------------------------
# Tags (US5)
# ---------------------------------------------------------------------------


def update_tags(
    db: Session,
    *,
    account_id: UUID | str,
    doc_id: UUID | str,
    user_id: UUID | str,
    tags: list[str],
) -> tuple[str, ...]:
    """Met à jour les tags d'un document ; retourne le tableau persisté."""
    row = db.execute(
        text(
            "SELECT COALESCE(tags, ARRAY[]::TEXT[]) AS tags FROM document_entreprise "
            "WHERE id = CAST(:id AS UUID) AND account_id = CAST(:aid AS UUID) "
            "AND deleted_at IS NULL"
        ),
        {"id": str(doc_id), "aid": str(account_id)},
    ).first()
    if row is None:
        raise DocumentNotFound()
    old_tags = tuple(row.tags or ())
    cleaned: list[str] = []
    for t in tags:
        s = (t or "").strip()
        if not s or len(s) > 40:
            continue
        if s in cleaned:
            continue
        cleaned.append(s)
    db.execute(
        text(
            "UPDATE document_entreprise SET tags = CAST(:tags AS TEXT[]), updated_at = now() "
            "WHERE id = CAST(:id AS UUID)"
        ),
        {"tags": cleaned, "id": str(doc_id)},
    )
    record_audit(
        db,
        entity_type="document_entreprise",
        entity_id=doc_id if isinstance(doc_id, UUID) else UUID(str(doc_id)),
        field="tags",
        old=list(old_tags),
        new=cleaned,
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
        notes="document_entreprise.update_tags",
    )
    return tuple(cleaned)


# ---------------------------------------------------------------------------
# Relance OCR
# ---------------------------------------------------------------------------


class OcrInProgress(Exception):
    pass


def relaunch_ocr(
    db: Session,
    *,
    account_id: UUID | str,
    doc_id: UUID | str,
    user_id: UUID | str,
    invalidate_existing_validation: bool,
) -> None:
    row = db.execute(
        text(
            "SELECT ocr_status FROM document_entreprise "
            "WHERE id = CAST(:id AS UUID) AND account_id = CAST(:aid AS UUID) "
            "AND deleted_at IS NULL"
        ),
        {"id": str(doc_id), "aid": str(account_id)},
    ).first()
    if row is None:
        raise DocumentNotFound()
    if row.ocr_status == "processing":
        raise OcrInProgress()

    extra_validate_clause = ""
    if invalidate_existing_validation:
        extra_validate_clause = (
            ", extraction_validated_at = NULL, extraction_validated_by = NULL"
        )
    db.execute(
        text(
            "UPDATE document_entreprise SET "
            f"ocr_status = 'pending'{extra_validate_clause}, "
            "updated_at = now() "
            "WHERE id = CAST(:id AS UUID)"
        ),
        {"id": str(doc_id)},
    )
    record_audit(
        db,
        entity_type="document_entreprise",
        entity_id=doc_id if isinstance(doc_id, UUID) else UUID(str(doc_id)),
        field="ocr_status",
        old=None,
        new={"action": "relaunch", "invalidates_validation": invalidate_existing_validation},
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
        notes="document_entreprise.relaunch_ocr",
    )
