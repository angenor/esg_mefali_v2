"""F22 - Service documents entreprise : upload / list / get / read / delete.

Calque ``app/projets/documents_service.py`` (F12) en remplacant ``projet_id``
par ``entreprise_id``. L'entreprise est resolue automatiquement depuis le
``account_id`` du PME courant (1 PME = 1 entreprise en MVP, cf. F11).

Apres l'INSERT (status pending), on appelle ``OcrService.extract_text``
de maniere synchrone et on UPDATE le statut + text_content + ocr_error.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.entreprise.documents_validators import (
    MAX_DOCS_PER_ENTREPRISE,
    ValidationError,
    validate_doc_type,
    validate_mime,
    validate_size,
)
from app.services.ocr_service import extract_text
from app.storage.base import Storage
from app.storage.fingerprint import sha256_bytes

_MIME_TO_EXT = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}


@dataclass(frozen=True)
class DocumentEntrepriseRow:
    id: UUID
    account_id: UUID
    entreprise_id: UUID
    name: str
    original_filename: str
    mime_type: str
    size_bytes: int
    type: str
    storage_path: str
    text_content: str | None
    ocr_status: str
    ocr_error: str | None
    uploaded_by: UUID | None
    created_at: datetime | None


class EntrepriseRequired(Exception):
    """Le compte n'a pas d'entreprise associee."""


class DocumentNotFound(Exception):
    pass


class TooManyDocuments(Exception):
    pass


def _resolve_entreprise_id(db: Session, account_id: UUID | str) -> UUID | None:
    row = db.execute(
        text(
            "SELECT id FROM entreprise WHERE account_id = CAST(:aid AS UUID) "
            "AND deleted_at IS NULL LIMIT 1"
        ),
        {"aid": str(account_id)},
    ).first()
    if row is None:
        return None
    return row.id


def _count_docs(db: Session, *, entreprise_id: UUID | str) -> int:
    return int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM document_entreprise "
                "WHERE entreprise_id = CAST(:eid AS UUID) AND deleted_at IS NULL"
            ),
            {"eid": str(entreprise_id)},
        ).scalar_one()
    )


def _row_to_dataclass(r) -> DocumentEntrepriseRow:
    return DocumentEntrepriseRow(
        id=r.id,
        account_id=r.account_id,
        entreprise_id=r.entreprise_id,
        name=r.name,
        original_filename=r.original_filename,
        mime_type=r.mime_type,
        size_bytes=int(r.size_bytes),
        type=r.type,
        storage_path=r.storage_path,
        text_content=r.text_content,
        ocr_status=r.ocr_status,
        ocr_error=r.ocr_error,
        uploaded_by=r.uploaded_by,
        created_at=r.created_at,
    )


_SELECT_COLS = (
    "id, account_id, entreprise_id, name, original_filename, mime_type, "
    "size_bytes, type, storage_path, text_content, ocr_status, ocr_error, "
    "uploaded_by, created_at"
)


def upload_document(
    db: Session,
    storage: Storage,
    *,
    account_id: UUID | str,
    user_id: UUID | str,
    name: str,
    original_filename: str,
    mime_type: str,
    size_bytes: int,
    doc_type: str,
    data: bytes,
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> DocumentEntrepriseRow:
    entreprise_id = _resolve_entreprise_id(db, account_id)
    if entreprise_id is None:
        raise EntrepriseRequired()

    validate_mime(mime_type)
    validate_size(size_bytes)
    validate_doc_type(doc_type)
    if size_bytes != len(data):
        raise ValidationError(
            "size_mismatch", "size_bytes ne correspond pas a len(data)"
        )

    if _count_docs(db, entreprise_id=entreprise_id) >= MAX_DOCS_PER_ENTREPRISE:
        raise TooManyDocuments(
            f"Maximum {MAX_DOCS_PER_ENTREPRISE} documents par entreprise atteint."
        )

    new_id = uuid.uuid4()
    ext = _MIME_TO_EXT.get(mime_type, "bin")
    rel_path = f"entreprise/{account_id}/{entreprise_id}/{new_id}.{ext}"
    storage.save(rel_path, data)

    # F50 — empreinte SHA-256 calculée serveur (jamais l'empreinte client seule).
    sha_hex = sha256_bytes(data)

    # Extraction OCR synchrone (FR-010, FR-015).
    outcome = extract_text(mime_type, data)

    db.execute(
        text(
            """
            INSERT INTO document_entreprise (
                id, account_id, entreprise_id, name, original_filename, mime_type,
                size_bytes, type, storage_path, text_content,
                ocr_status, ocr_error, uploaded_by, source_of_change,
                version, content_sha256, created_at, updated_at
            )
            VALUES (
                CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:eid AS UUID),
                :name, :ofn, :mt, :sz, :type, :sp, :txt,
                :ostatus, :oerr, CAST(:uid AS UUID), :soc, 1,
                decode(:sha, 'hex'), now(), now()
            )
            """
        ),
        {
            "id": str(new_id),
            "aid": str(account_id),
            "eid": str(entreprise_id),
            "name": name,
            "ofn": original_filename,
            "mt": mime_type,
            "sz": size_bytes,
            "type": doc_type,
            "sp": rel_path,
            "txt": outcome.text,
            "ostatus": outcome.status,
            "oerr": outcome.error,
            "uid": str(user_id) if user_id else None,
            "soc": (
                source_of_change.value
                if isinstance(source_of_change, SourceOfChange)
                else str(source_of_change)
            ),
            "sha": sha_hex,
        },
    )
    db.flush()

    record_audit(
        db,
        entity_type="document_entreprise",
        entity_id=new_id,
        field=None,
        old=None,
        new={
            "entreprise_id": str(entreprise_id),
            "name": name,
            "type": doc_type,
            "size": size_bytes,
            "ocr_status": outcome.status,
        },
        source_of_change=source_of_change,
        user_id=user_id,
        account_id=account_id,
        notes="document_entreprise.uploaded",
    )

    row = db.execute(
        text(f"SELECT {_SELECT_COLS} FROM document_entreprise WHERE id = CAST(:id AS UUID)"),
        {"id": str(new_id)},
    ).first()
    if row is None:
        raise RuntimeError("document_entreprise vanished after insert")
    return _row_to_dataclass(row)


def list_documents(
    db: Session, *, account_id: UUID | str
) -> list[DocumentEntrepriseRow]:
    entreprise_id = _resolve_entreprise_id(db, account_id)
    if entreprise_id is None:
        raise EntrepriseRequired()
    rows = db.execute(
        text(
            f"SELECT {_SELECT_COLS} FROM document_entreprise "
            "WHERE entreprise_id = CAST(:eid AS UUID) AND deleted_at IS NULL "
            "ORDER BY created_at DESC"
        ),
        {"eid": str(entreprise_id)},
    ).all()
    return [_row_to_dataclass(r) for r in rows]


def get_document(
    db: Session, *, doc_id: UUID | str, account_id: UUID | str
) -> DocumentEntrepriseRow:
    row = db.execute(
        text(
            f"SELECT {_SELECT_COLS} FROM document_entreprise "
            "WHERE id = CAST(:did AS UUID) AND account_id = CAST(:aid AS UUID) "
            "AND deleted_at IS NULL"
        ),
        {"did": str(doc_id), "aid": str(account_id)},
    ).first()
    if row is None:
        raise DocumentNotFound()
    return _row_to_dataclass(row)


def read_document(
    db: Session,
    storage: Storage,
    *,
    doc_id: UUID | str,
    account_id: UUID | str,
    user_id: UUID | str | None = None,
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> tuple[DocumentEntrepriseRow, bytes]:
    row = get_document(db, doc_id=doc_id, account_id=account_id)
    record_audit(
        db,
        entity_type="document_entreprise",
        entity_id=row.id,
        field=None,
        old=None,
        new={"action": "downloaded"},
        source_of_change=source_of_change,
        user_id=user_id,
        account_id=account_id,
        notes="document_entreprise.downloaded",
    )
    return row, storage.read(row.storage_path)


def delete_document(
    db: Session,
    storage: Storage,
    *,
    doc_id: UUID | str,
    account_id: UUID | str,
    user_id: UUID | str,
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> None:
    row = get_document(db, doc_id=doc_id, account_id=account_id)
    # F50 US6 — soft-delete avec purge_scheduled_at = deleted_at + 30 jours.
    # Le fichier physique reste sur disque jusqu'au job de purge.
    from app.entreprise.documents_validators import DOCUMENT_PURGE_DAYS
    db.execute(
        text(
            f"UPDATE document_entreprise SET deleted_at = now(), "
            f"purge_scheduled_at = now() + interval '{DOCUMENT_PURGE_DAYS} days', "
            f"updated_at = now() "
            f"WHERE id = CAST(:id AS UUID)"
        ),
        {"id": str(row.id)},
    )

    record_audit(
        db,
        entity_type="document_entreprise",
        entity_id=row.id,
        field="deleted_at",
        old=None,
        new="now",
        source_of_change=source_of_change,
        user_id=user_id,
        account_id=account_id,
        notes="document_entreprise.deleted",
    )
