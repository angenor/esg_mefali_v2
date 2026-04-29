"""F22 - Routes API documents entreprise (/me/entreprise/documents).

Calque ``app/api/routes/projets_documents.py`` (F12) en remplacant
``projet_id`` par la resolution implicite de l'entreprise du PME courant
(1 PME = 1 entreprise en MVP, cf. F11).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.config import get_settings
from app.db import get_db
from app.entreprise.documents_service import (
    DocumentEntrepriseRow,
    DocumentNotFound,
    EntrepriseRequired,
    TooManyDocuments,
    delete_document,
    get_document,
    list_documents,
    read_document,
    upload_document,
)
from app.entreprise.documents_validators import ValidationError as EntrepriseValidationError
from app.models.account_user import AccountUser
from app.storage.local import LocalStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/entreprise", tags=["entreprise-documents"])


def get_storage() -> LocalStorage:
    settings = get_settings()
    root = getattr(settings, "storage_root", None) or "backend/storage"
    return LocalStorage(root)


def _serialize(row: DocumentEntrepriseRow) -> dict[str, Any]:
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
    }


@router.get("/documents")
def list_endpoint(
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    try:
        rows = list_documents(db, account_id=user.account_id)
    except EntrepriseRequired as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "entreprise_required",
                "message": "Aucune entreprise associee a ce compte.",
            },
        ) from exc
    return {"items": [_serialize(r) for r in rows]}


@router.post("/documents", status_code=201)
async def upload_endpoint(
    file: UploadFile = File(...),
    type: str = Form(...),
    name: str | None = Form(default=None),
    storage: LocalStorage = Depends(get_storage),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    data = await file.read()
    size = len(data)
    mime = file.content_type or "application/octet-stream"
    display_name = name or file.filename or "document"

    try:
        row = upload_document(
            db,
            storage,
            account_id=user.account_id,
            user_id=user.id,
            name=display_name,
            original_filename=file.filename or display_name,
            mime_type=mime,
            size_bytes=size,
            doc_type=type,
            data=data,
        )
    except EntrepriseRequired as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "entreprise_required",
                "message": "Aucune entreprise associee a ce compte.",
            },
        ) from exc
    except TooManyDocuments as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "too_many_documents", "message": str(exc)},
        ) from exc
    except EntrepriseValidationError as exc:
        if exc.code == "size_too_large":
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"code": exc.code, "message": exc.message},
            ) from exc
        if exc.code == "mime_not_allowed":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={"code": exc.code, "message": exc.message},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    db.commit()
    return _serialize(row)


@router.get("/documents/{doc_id}")
def detail_endpoint(
    doc_id: str,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    try:
        row = get_document(db, doc_id=doc_id, account_id=user.account_id)
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    return _serialize(row)


@router.get("/documents/{doc_id}/download")
def download_endpoint(
    doc_id: str,
    storage: LocalStorage = Depends(get_storage),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Response:
    try:
        row, data = read_document(
            db,
            storage,
            doc_id=doc_id,
            account_id=user.account_id,
            user_id=user.id,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    db.commit()
    return Response(
        content=data,
        media_type=row.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{row.original_filename}"'
        },
    )


@router.delete("/documents/{doc_id}", status_code=204)
def delete_endpoint(
    doc_id: str,
    storage: LocalStorage = Depends(get_storage),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> None:
    try:
        get_document(db, doc_id=doc_id, account_id=user.account_id)
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    delete_document(
        db,
        storage,
        doc_id=doc_id,
        account_id=user.account_id,
        user_id=user.id,
    )
    db.commit()
