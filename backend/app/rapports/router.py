"""F24 — Routes API ``/me/rapports/*`` (PME)."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.config import get_settings
from app.db import get_db
from app.models.account_user import AccountUser
from app.rapports.schemas import (
    RapportCreateIn,
    RapportListOut,
    RapportOut,
)
from app.rapports.service import (
    generate_rapport,
    get_rapport,
    list_rapports,
)
from app.scoring.service import EntityNotAccessible

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/rapports", tags=["rapports"])


def _to_out(row: dict) -> RapportOut:
    return RapportOut(
        rapport_id=row["rapport_id"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        referentiels=row["referentiels"],
        language=row["language"],
        file_size_bytes=row.get("file_size_bytes"),
        generated_at=row["generated_at"],
        download_url=f"/me/rapports/{row['rapport_id']}/download",
    )


@router.post(
    "/conformite",
    response_model=RapportOut,
    status_code=status.HTTP_201_CREATED,
)
def create_rapport(
    body: RapportCreateIn,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> RapportOut:
    """Génère un rapport PDF de conformité ESG pour l'entité demandée."""
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        result = generate_rapport(
            db,
            account_id=user.account_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            referentiels=body.referentiels,
            language=body.language,
            user_id=user.id,
        )
    except EntityNotAccessible as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entité hors tenant",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    db.commit()
    return _to_out(result)


@router.get("", response_model=RapportListOut)
def list_my_rapports(
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> RapportListOut:
    """Liste les rapports générés par l'account courant."""
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if entity_type is not None and entity_type not in {"entreprise", "projet"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"entity_type invalide: {entity_type}",
        )
    rows = list_rapports(
        db,
        account_id=user.account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    items = [_to_out(r) for r in rows]
    return RapportListOut(items=items, total=len(items))


@router.get("/{rapport_id}/download")
def download_rapport(
    rapport_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> FileResponse:
    """Télécharge le PDF d'un rapport (RLS filtré)."""
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    row = get_rapport(
        db, account_id=user.account_id, rapport_id=rapport_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    file_path = Path(row["file_path"])
    if not file_path.exists():
        logger.error(
            "rapport.file_missing rapport_id=%s path=%s",
            rapport_id,
            file_path,
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="fichier rapport introuvable sur disque",
        )
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"rapport-esg-{rapport_id}.pdf",
    )


# ---------------------------------------------------------------------------
# F49 T006 — SSE de progression de génération
#
# Le backend F24 actuel génère les rapports de manière synchrone : le rapport
# existe dès que le POST /me/rapports/conformite revient. Cet endpoint SSE
# fournit néanmoins le contrat attendu par l'UI F49 : il interroge la table
# rapport_genere et émet, dès que la ligne existe, une séquence courte
# `progress` → `done`. Si la ligne n'apparaît pas dans le délai imparti il
# émet `failed`. Le `Last-Event-ID` est honoré (les événements sont indexés).
# ---------------------------------------------------------------------------


_SSE_POLL_INTERVAL_S = 0.5
_SSE_MAX_WAIT_S = 60.0


def _sse(event: str, data: dict, event_id: int) -> bytes:
    return (
        f"id: {event_id}\nevent: {event}\n"
        f"data: {json.dumps(data, separators=(',', ':'))}\n\n"
    ).encode()


@router.get("/generate/{generation_id}/stream")
async def stream_generation(
    generation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> StreamingResponse:
    """SSE — émet `progress` puis `done`/`failed` pour une génération.

    Convention F49 (adaptation au backend synchrone) :
      * `generation_id == rapport_id` ;
      * dès que la ligne `rapport_genere` est visible (RLS actif), l'endpoint
        émet `progress 0/50/100` puis `done` ; sinon `failed` après timeout.
    """
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    last_id_hdr = request.headers.get("last-event-id")
    try:
        last_id = int(last_id_hdr) if last_id_hdr else 0
    except ValueError:
        last_id = 0

    aid = user.account_id

    async def _gen():
        events_emitted = 0
        deadline = time.monotonic() + _SSE_MAX_WAIT_S
        steps = (
            (1, "progress", {"step": "queued", "percent": 0}),
            (2, "progress", {"step": "rendering", "percent": 50}),
        )
        while time.monotonic() < deadline:
            if await request.is_disconnected():
                return
            row = get_rapport(db, account_id=aid, rapport_id=generation_id)
            if row is not None:
                for eid, name, data in steps:
                    if eid > last_id:
                        yield _sse(name, data, eid)
                        events_emitted += 1
                done_id = 3
                if done_id > last_id:
                    yield _sse(
                        "done",
                        {
                            "rapport_id": str(row["rapport_id"]),
                            "download_filename": (
                                f"rapport-esg-{row['rapport_id']}.pdf"
                            ),
                        },
                        done_id,
                    )
                    events_emitted += 1
                return
            await asyncio.sleep(_SSE_POLL_INTERVAL_S)
        # timeout : aucune ligne créée → failed
        if 99 > last_id:
            yield _sse(
                "failed",
                {"error": "generation_timeout"},
                99,
            )
        _ = events_emitted

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# F49 T007/T008 — URL signée pour aperçu PDF (TTL 5 min)
# ---------------------------------------------------------------------------


_PREVIEW_TTL_S = 300


def _preview_secret() -> bytes:
    """Réutilise JWT_SECRET pour signer les URL d'aperçu (HMAC-SHA256).

    Dérivation déterministe pour ne pas ajouter de variable d'environnement.
    """
    return hashlib.sha256(
        get_settings().JWT_SECRET.encode("utf-8") + b"\x00rapport-preview"
    ).digest()


def _sign_preview(rapport_id: uuid.UUID, account_id: uuid.UUID, exp_ts: int) -> str:
    msg = f"{rapport_id}|{account_id}|{exp_ts}".encode()
    return hmac.new(_preview_secret(), msg, hashlib.sha256).hexdigest()


@router.get("/{rapport_id}/preview-url")
def get_preview_url(
    rapport_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> dict:
    """Retourne `{url, expires_at}` — URL signée TTL 5 min pour aperçu inline."""
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    row = get_rapport(db, account_id=user.account_id, rapport_id=rapport_id)
    if row is None:
        # P2 : cross-tenant → 404, jamais 403
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    exp_ts = int(time.time()) + _PREVIEW_TTL_S
    sig = _sign_preview(rapport_id, user.account_id, exp_ts)
    base = str(request.base_url).rstrip("/")
    url = (
        f"{base}/me/rapports/{rapport_id}/preview"
        f"?aid={user.account_id}&t={exp_ts}&sig={sig}"
    )
    from datetime import UTC, datetime

    return {
        "url": url,
        "expires_at": datetime.fromtimestamp(exp_ts, tz=UTC).isoformat(),
    }


@router.get("/{rapport_id}/preview")
def serve_preview(
    rapport_id: uuid.UUID,
    aid: uuid.UUID,
    t: int,
    sig: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Sert le PDF en inline si la signature HMAC est valide et non expirée.

    N'exige **aucune** session : la signature est tenant-bound (porte
    `account_id`). En cas d'échec on retourne 404 (pas 401/403).
    """
    from sqlalchemy import text as _sql_text

    if int(time.time()) > t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    expected = _sign_preview(rapport_id, aid, t)
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    # La signature porte le `account_id` ; on positionne le GUC RLS pour la
    # lecture (pas de session PME ici).
    db.execute(
        _sql_text("SELECT set_config('app.current_account_id', :aid, true)"),
        {"aid": str(aid)},
    )
    row = get_rapport(db, account_id=aid, rapport_id=rapport_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    file_path = Path(row["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        # inline (pas attachment) pour permettre l'iframe
        headers={"Content-Disposition": "inline"},
    )
