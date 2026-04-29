"""F12 - Service documents projet : upload / list / read / delete."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.projets.events import publish_sync
from app.projets.validators import (
    MAX_DOCS_PER_PROJET,
    ValidationError,
    validate_doc_type,
    validate_mime,
    validate_size,
)
from app.storage.base import Storage

_MIME_TO_EXT = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


@dataclass(frozen=True)
class DocumentProjetRow:
    id: UUID
    projet_id: UUID
    account_id: UUID
    name: str
    original_filename: str
    mime_type: str
    size_bytes: int
    type: str
    storage_path: str
    uploaded_by: UUID | None
    created_at: datetime | None


class ProjetNotFound(Exception):
    pass


class DocumentNotFound(Exception):
    pass


class TooManyDocuments(Exception):
    pass


def _projet_exists_for_account(db: Session, *, projet_id: UUID | str, account_id: UUID | str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM projet WHERE id = CAST(:pid AS UUID) "
            "AND account_id = CAST(:aid AS UUID) AND deleted_at IS NULL LIMIT 1"
        ),
        {"pid": str(projet_id), "aid": str(account_id)},
    ).first()
    return row is not None


def _count_docs(db: Session, *, projet_id: UUID | str) -> int:
    return int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM document_projet "
                "WHERE projet_id = CAST(:pid AS UUID) AND deleted_at IS NULL"
            ),
            {"pid": str(projet_id)},
        ).scalar_one()
    )


def _row_to_dataclass(r) -> DocumentProjetRow:
    return DocumentProjetRow(
        id=r.id, projet_id=r.projet_id, account_id=r.account_id,
        name=r.name, original_filename=r.original_filename,
        mime_type=r.mime_type, size_bytes=int(r.size_bytes),
        type=r.type, storage_path=r.storage_path,
        uploaded_by=r.uploaded_by, created_at=r.created_at,
    )


def upload_document(
    db: Session,
    storage: Storage,
    *,
    projet_id: UUID | str,
    account_id: UUID | str,
    user_id: UUID | str,
    name: str,
    original_filename: str,
    mime_type: str,
    size_bytes: int,
    doc_type: str,
    data: bytes,
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> DocumentProjetRow:
    if not _projet_exists_for_account(db, projet_id=projet_id, account_id=account_id):
        raise ProjetNotFound()
    validate_mime(mime_type)
    validate_size(size_bytes)
    validate_doc_type(doc_type)
    if size_bytes != len(data):
        raise ValidationError("size_mismatch", "size_bytes ne correspond pas a len(data)")

    if _count_docs(db, projet_id=projet_id) >= MAX_DOCS_PER_PROJET:
        raise TooManyDocuments(
            f"Maximum {MAX_DOCS_PER_PROJET} documents par projet atteint."
        )

    new_id = uuid.uuid4()
    ext = _MIME_TO_EXT.get(mime_type, "bin")
    rel_path = f"projets/{account_id}/{projet_id}/{new_id}.{ext}"
    storage.save(rel_path, data)

    sql = text(
        """
        INSERT INTO document_projet (
            id, account_id, projet_id, name, original_filename, mime_type,
            size_bytes, type, storage_path, uploaded_by, source_of_change,
            version, created_at, updated_at
        )
        VALUES (
            CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:pid AS UUID),
            :name, :ofn, :mt, :sz, :type, :sp,
            CAST(:uid AS UUID), :soc, 1, now(), now()
        )
        """
    )
    db.execute(
        sql,
        {
            "id": str(new_id),
            "aid": str(account_id),
            "pid": str(projet_id),
            "name": name,
            "ofn": original_filename,
            "mt": mime_type,
            "sz": size_bytes,
            "type": doc_type,
            "sp": rel_path,
            "uid": str(user_id) if user_id else None,
            "soc": (
                source_of_change.value
                if isinstance(source_of_change, SourceOfChange)
                else str(source_of_change)
            ),
        },
    )
    db.flush()

    record_audit(
        db,
        entity_type="document_projet",
        entity_id=new_id,
        field=None,
        old=None,
        new={"projet_id": str(projet_id), "name": name, "type": doc_type, "size": size_bytes},
        source_of_change=source_of_change,
        user_id=user_id,
        account_id=account_id,
        notes="document_projet.uploaded",
    )

    publish_sync(
        account_id,
        {
            "type": "projet.document.added",
            "projet_id": str(projet_id),
            "document_id": str(new_id),
            "name": name,
        },
    )

    row = db.execute(
        text(
            "SELECT id, projet_id, account_id, name, original_filename, mime_type, "
            "size_bytes, type, storage_path, uploaded_by, created_at "
            "FROM document_projet WHERE id = CAST(:id AS UUID)"
        ),
        {"id": str(new_id)},
    ).first()
    if row is None:
        raise RuntimeError("document_projet vanished after insert")
    return _row_to_dataclass(row)


def list_documents(
    db: Session, *, projet_id: UUID | str, account_id: UUID | str
) -> list[DocumentProjetRow]:
    if not _projet_exists_for_account(db, projet_id=projet_id, account_id=account_id):
        raise ProjetNotFound()
    rows = db.execute(
        text(
            "SELECT id, projet_id, account_id, name, original_filename, mime_type, "
            "size_bytes, type, storage_path, uploaded_by, created_at "
            "FROM document_projet "
            "WHERE projet_id = CAST(:pid AS UUID) AND deleted_at IS NULL "
            "ORDER BY created_at DESC"
        ),
        {"pid": str(projet_id)},
    ).all()
    return [_row_to_dataclass(r) for r in rows]


def get_document(
    db: Session, *, doc_id: UUID | str, projet_id: UUID | str, account_id: UUID | str
) -> DocumentProjetRow:
    row = db.execute(
        text(
            "SELECT id, projet_id, account_id, name, original_filename, mime_type, "
            "size_bytes, type, storage_path, uploaded_by, created_at "
            "FROM document_projet "
            "WHERE id = CAST(:did AS UUID) AND projet_id = CAST(:pid AS UUID) "
            "AND account_id = CAST(:aid AS UUID) AND deleted_at IS NULL"
        ),
        {"did": str(doc_id), "pid": str(projet_id), "aid": str(account_id)},
    ).first()
    if row is None:
        raise DocumentNotFound()
    return _row_to_dataclass(row)


def read_document(
    db: Session, storage: Storage, *, doc_id: UUID | str,
    projet_id: UUID | str, account_id: UUID | str,
) -> tuple[DocumentProjetRow, bytes]:
    row = get_document(db, doc_id=doc_id, projet_id=projet_id, account_id=account_id)
    return row, storage.read(row.storage_path)


def delete_document(
    db: Session, storage: Storage, *,
    doc_id: UUID | str, projet_id: UUID | str, account_id: UUID | str,
    user_id: UUID | str,
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> None:
    row = get_document(db, doc_id=doc_id, projet_id=projet_id, account_id=account_id)
    db.execute(
        text(
            "UPDATE document_projet SET deleted_at = now(), updated_at = now() "
            "WHERE id = CAST(:id AS UUID)"
        ),
        {"id": str(row.id)},
    )
    try:
        storage.delete(row.storage_path)
    except OSError:
        # Soft-delete deja effectue; on tolere une erreur d'IO sur le FS.
        pass

    record_audit(
        db,
        entity_type="document_projet",
        entity_id=row.id,
        field="deleted_at",
        old=None,
        new="now",
        source_of_change=source_of_change,
        user_id=user_id,
        account_id=account_id,
        notes="document_projet.deleted",
    )
    publish_sync(
        account_id,
        {
            "type": "projet.document.deleted",
            "projet_id": str(projet_id),
            "document_id": str(row.id),
        },
    )
