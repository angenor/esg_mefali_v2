"""F12 - Routes API documents projet (/me/projets/{id}/documents)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.config import get_settings
from app.db import get_db
from app.models.account_user import AccountUser
from app.projets.documents_service import (
    DocumentNotFound,
    ProjetNotFound,
    TooManyDocuments,
    delete_document,
    get_document,
    list_documents,
    read_document,
    upload_document,
)
from app.projets.validators import ValidationError as ProjetValidationError
from app.storage.local import LocalStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/projets", tags=["projets-documents"])


def get_storage() -> LocalStorage:
    settings = get_settings()
    root = getattr(settings, "storage_root", None) or "backend/storage"
    return LocalStorage(root)


@router.get("/{projet_id}/documents")
def list_endpoint(
    projet_id: str,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    try:
        rows = list_documents(db, projet_id=projet_id, account_id=user.account_id)
    except ProjetNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    return {
        "items": [
            {
                "id": str(r.id),
                "projet_id": str(r.projet_id),
                "name": r.name,
                "original_filename": r.original_filename,
                "mime_type": r.mime_type,
                "size_bytes": r.size_bytes,
                "type": r.type,
                "uploaded_by": str(r.uploaded_by) if r.uploaded_by else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.post("/{projet_id}/documents", status_code=201)
async def upload_endpoint(
    projet_id: str,
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
            projet_id=projet_id,
            account_id=user.account_id,
            user_id=user.id,
            name=display_name,
            original_filename=file.filename or display_name,
            mime_type=mime,
            size_bytes=size,
            doc_type=type,
            data=data,
        )
    except ProjetNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    except TooManyDocuments as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "too_many_documents", "message": str(exc)},
        ) from exc
    except ProjetValidationError as exc:
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
    return {
        "id": str(row.id),
        "projet_id": str(row.projet_id),
        "name": row.name,
        "original_filename": row.original_filename,
        "mime_type": row.mime_type,
        "size_bytes": row.size_bytes,
        "type": row.type,
    }


@router.get("/{projet_id}/documents/{doc_id}/download")
def download_endpoint(
    projet_id: str,
    doc_id: str,
    storage: LocalStorage = Depends(get_storage),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Response:
    try:
        row, data = read_document(
            db, storage,
            doc_id=doc_id, projet_id=projet_id, account_id=user.account_id,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    return Response(
        content=data,
        media_type=row.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{row.original_filename}"'},
    )


@router.delete("/{projet_id}/documents/{doc_id}", status_code=204)
def delete_endpoint(
    projet_id: str,
    doc_id: str,
    storage: LocalStorage = Depends(get_storage),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> None:
    try:
        get_document(db, doc_id=doc_id, projet_id=projet_id, account_id=user.account_id)
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    delete_document(
        db, storage,
        doc_id=doc_id, projet_id=projet_id,
        account_id=user.account_id, user_id=user.id,
    )
    db.commit()
