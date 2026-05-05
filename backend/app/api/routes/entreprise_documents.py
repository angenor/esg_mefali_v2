"""F22 - Routes API documents entreprise (/me/entreprise/documents).

Calque ``app/api/routes/projets_documents.py`` (F12) en remplacant
``projet_id`` par la resolution implicite de l'entreprise du PME courant
(1 PME = 1 entreprise en MVP, cf. F11).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.config import get_settings
from app.core.rate_limit import check_rate
from app.db import get_db
from app.entreprise.documents_f50 import (
    CrossAccountProjet,
    ProjetNotFound,
    _fetch_extras,
    link_document_to_projet,
    serialize_document,
)
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


def _serialize(row: DocumentEntrepriseRow, db: Session | None = None) -> dict[str, Any]:
    """Sérialise en forme F50 (extras chargés si ``db`` fourni)."""
    extras = _fetch_extras(db, row.id) if db is not None else None
    return serialize_document(row, extras)


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
    return {"items": [_serialize(r, db) for r in rows]}


@router.post("/documents", status_code=201)
async def upload_endpoint(
    request: Request,
    file: UploadFile = File(...),
    type: str = Form(...),
    name: str | None = Form(default=None),
    client_sha256: str | None = Form(default=None),  # F50 — indicatif
    link_projet_id: str | None = Form(default=None),  # F50 — M:N upload
    storage: LocalStorage = Depends(get_storage),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    # H5: rate-limit upload (DoS file flood mitigation).
    check_rate(request, "documents.upload", "10/minute")
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
    # F50 — lien projet à la création (best-effort).
    if link_projet_id:
        # H2: parser l'UUID avant l'appel service pour éviter une 500 sur CAST PG.
        try:
            projet_uuid = UUID(link_projet_id)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "invalid_projet_id"},
            ) from exc
        try:
            link_document_to_projet(
                db,
                account_id=user.account_id,
                doc_id=row.id,
                projet_id=str(projet_uuid),
                user_id=user.id,
            )
        except ProjetNotFound as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "projet_not_found"},
            ) from exc
        except CrossAccountProjet as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "same_account_required"},
            ) from exc
    # F50 — sérialiser AVANT commit : ``SET LOCAL app.current_account_id``
    # ne survit pas au commit, donc ``_fetch_extras`` perdrait la visibilité
    # RLS sur ``document_link_projet`` et retournerait ``linked_projets=[]``.
    result = _serialize(row, db)
    db.commit()
    return result


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
    return _serialize(row, db)


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
