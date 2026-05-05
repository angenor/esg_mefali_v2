"""F50 — Routes additionnelles pour documents/F50 (fingerprint, validate, link, relaunch).

Monté en plus du router F22 ``entreprise_documents.py`` avec deux préfixes :
 - ``/me/documents`` pour le pre-flight by-fingerprint (lookup global compte).
 - ``/me/entreprise/documents/...`` pour validate / relaunch / link / unlink.

Les endpoints F22 existants (``GET /``, ``POST /``, ``GET /{id}``, ``DELETE /{id}``)
restent dans le router F22 ; F50 ne fait que les compléter.
"""

from __future__ import annotations

import logging
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.entreprise.documents_f50 import (
    AlreadyValidated,
    CrossAccountProjet,
    OcrInProgress,
    ProjetNotFound,
    _fetch_extras,
    find_by_fingerprint,
    link_document_to_projet,
    relaunch_ocr,
    serialize_document,
    soft_delete_with_purge,
    unlink_document_from_projet,
    update_tags,
    validate_extraction,
)
from app.entreprise.documents_service import (
    DocumentNotFound,
    EntrepriseRequired,
    get_document,
)
from app.models.account_user import AccountUser
from app.storage.fingerprint import is_valid_sha256_hex

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schémas Pydantic v2 (extra='forbid' — P9)
# ---------------------------------------------------------------------------


class ValidateExtractionFieldIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    value: Any = None


class PropagationTargetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity: Literal["entreprise", "projet"]
    id: UUID


class ValidateExtractionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fields: list[ValidateExtractionFieldIn]
    propagate_to: list[PropagationTargetIn] = Field(default_factory=list)


class LinkProjetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    projet_id: UUID


class RelaunchOcrIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invalidate_existing_validation: bool = False


class UpdateTagsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tags: list[str] = Field(default_factory=list, max_length=20)


# ---------------------------------------------------------------------------
# Router fingerprint (compte global)
# ---------------------------------------------------------------------------

fingerprint_router = APIRouter(prefix="/me/documents", tags=["documents-f50"])


@fingerprint_router.get("/by-fingerprint")
def by_fingerprint_endpoint(
    sha256: str,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    if not is_valid_sha256_hex(sha256):
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_fingerprint", "message": "Empreinte SHA-256 hex requise (64 chars)."},
        )
    row = find_by_fingerprint(db, account_id=user.account_id, sha256_hex=sha256)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    extras = _fetch_extras(db, row.id)
    return {"document": serialize_document(row, extras)}


# ---------------------------------------------------------------------------
# Router F50 sur /me/entreprise/documents/{id}/...
# ---------------------------------------------------------------------------

f50_router = APIRouter(
    prefix="/me/entreprise/documents", tags=["documents-f50"]
)


@f50_router.post("/{doc_id}/validate")
def validate_endpoint(
    doc_id: UUID,
    payload: ValidateExtractionIn,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    fields = [f.model_dump() for f in payload.fields]
    targets = [t.model_dump(mode="json") for t in payload.propagate_to]
    try:
        result = validate_extraction(
            db,
            account_id=user.account_id,
            doc_id=doc_id,
            user_id=user.id,
            fields=fields,
            propagate_to=targets,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    except AlreadyValidated as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "already_validated",
                "message": "Document déjà validé. Utilisez la re-correction.",
            },
        ) from exc
    db.commit()
    return result


@f50_router.post("/{doc_id}/relaunch-ocr", status_code=202)
def relaunch_ocr_endpoint(
    doc_id: UUID,
    payload: RelaunchOcrIn,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    try:
        relaunch_ocr(
            db,
            account_id=user.account_id,
            doc_id=doc_id,
            user_id=user.id,
            invalidate_existing_validation=payload.invalidate_existing_validation,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    except OcrInProgress as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ocr_in_progress", "message": "Extraction déjà en cours."},
        ) from exc
    db.commit()
    return {"id": str(doc_id), "ocr_status": "pending"}


@f50_router.post("/{doc_id}/link-projet", status_code=201)
def link_projet_endpoint(
    doc_id: UUID,
    payload: LinkProjetIn,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    try:
        get_document(db, doc_id=doc_id, account_id=user.account_id)
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    except EntrepriseRequired as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "entreprise_required"},
        ) from exc
    try:
        created = link_document_to_projet(
            db,
            account_id=user.account_id,
            doc_id=doc_id,
            projet_id=payload.projet_id,
            user_id=user.id,
        )
    except ProjetNotFound as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "projet_not_found", "message": "Projet inconnu."},
        ) from exc
    except CrossAccountProjet as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "same_account_required",
                "message": "Le projet doit appartenir au même compte.",
            },
        ) from exc
    db.commit()
    return {"document_id": str(doc_id), "projet_id": str(payload.projet_id), "created": created}


@f50_router.delete("/{doc_id}/link-projet/{projet_id}", status_code=204)
def unlink_projet_endpoint(
    doc_id: UUID,
    projet_id: UUID,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> None:
    unlink_document_from_projet(
        db,
        account_id=user.account_id,
        doc_id=doc_id,
        projet_id=projet_id,
        user_id=user.id,
    )
    db.commit()
    return None


@f50_router.patch("/{doc_id}/tags")
def update_tags_endpoint(
    doc_id: UUID,
    payload: UpdateTagsIn,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    try:
        tags = update_tags(
            db,
            account_id=user.account_id,
            doc_id=doc_id,
            user_id=user.id,
            tags=payload.tags,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    # Sérialiser AVANT commit : ``SET LOCAL app.current_account_id`` ne
    # survit pas à un commit, donc les SELECT ultérieurs perdraient la
    # visibilité RLS.
    from app.entreprise.documents_service import get_document as _get
    row = _get(db, doc_id=doc_id, account_id=user.account_id)
    extras = _fetch_extras(db, doc_id)
    out = serialize_document(row, extras)
    out["tags"] = list(tags)
    db.commit()
    return out


@f50_router.delete("/{doc_id}/with-purge", status_code=204)
def soft_delete_with_purge_endpoint(
    doc_id: UUID,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete F50 (avec ``purge_scheduled_at = +30 jours``).

    NB : l'endpoint F22 ``DELETE /documents/{id}`` historique reste actif ;
    cet endpoint distinct est utilisé pour US6 quand on veut explicitement
    déclencher la programmation de purge.
    """
    try:
        soft_delete_with_purge(
            db,
            account_id=user.account_id,
            doc_id=doc_id,
            user_id=user.id,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    db.commit()
    return None
