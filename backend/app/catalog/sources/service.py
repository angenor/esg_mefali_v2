"""F07 — Service ``catalog/sources`` (US1, US2 partiel).

Responsabilités :
- canonicalise l'URL avant persistance (FR-002).
- détecte les doublons sur ``(canonical_url, COALESCE(page,''))`` (FR-003).
- inscrit un audit_log via ``app.audit.helper.record_audit`` (Module 0).
- HEAD probe non bloquant via ``http_probe.probe_url`` (FR-007) — best effort.

NOTE : pour la création/lecture en P1, on s'appuie sur l'existant
``app.services.source_service.create_pending`` qui couvre déjà l'insertion
de base, l'embedding placeholder, etc. Notre service ajoute une couche
métier (canonicalisation, détection de doublons, head_warning).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.catalog.sources.canonicalize import canonicalize_url
from app.catalog.sources.http_probe import probe_url
from app.catalog.sources.schemas import SourceCreate

ERROR_DUPLICATE = "duplicate_source"


def find_duplicate(
    db: Session, *, canonical_url: str, page: str | None
) -> uuid.UUID | None:
    """Retourne l'``id`` d'une source existante au même canonical_url+page,
    sinon ``None``.
    """
    row = db.execute(
        text(
            "SELECT id FROM source "
            "WHERE canonical_url = :u "
            "  AND COALESCE(page, '') = COALESCE(:p, '') "
            "LIMIT 1"
        ),
        {"u": canonical_url, "p": page},
    ).first()
    return uuid.UUID(str(row[0])) if row else None


async def _run_probe(canonical_url: str) -> str | None:
    """Lance le probe HEAD avec timeout. Retourne un message warning ou None."""
    try:
        result = await asyncio.wait_for(probe_url(canonical_url), timeout=6.0)
    except TimeoutError:
        return "URL probe timed out"
    if result["ok"]:
        return None
    if result["error"] == "timeout":
        return "URL probe timed out"
    if result["error"] == "network":
        return "URL probe network error"
    if result["status"] is not None:
        return f"URL probe returned HTTP {result['status']}"
    return "URL probe failed"


def create_source(
    db: Session,
    payload: SourceCreate,
    *,
    actor_id: uuid.UUID,
    run_probe: bool = True,
) -> tuple[dict[str, Any], str | None]:
    """Crée une nouvelle source en statut ``pending``.

    Args:
        db: session SQLAlchemy.
        payload: schéma validé Pydantic.
        actor_id: id de l'admin qui capture la source.
        run_probe: désactivable pour les tests offline.

    Returns:
        ``(source_row_dict, head_warning)``.

    Raises:
        HTTPException 409 si doublon canonical_url + page.
    """
    canonical = canonicalize_url(str(payload.url))

    existing_id = find_duplicate(db, canonical_url=canonical, page=payload.page)
    if existing_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": ERROR_DUPLICATE,
                "message": "Une source avec cette URL canonique et cette page existe déjà.",
                "existing_id": str(existing_id),
            },
        )

    head_warning: str | None = None
    if run_probe:
        try:
            head_warning = asyncio.run(_run_probe(canonical))
        except RuntimeError:
            # Si on est déjà dans une boucle asyncio (FastAPI sync route), on
            # skip le probe — il sera réexécuté en background ailleurs.
            head_warning = None

    sid = uuid.uuid4()
    # Note : nous insérons en SQL brut (pas d'ORM) pour rester cohérent avec
    # ``app.services.source_service.create_pending`` et éviter les frictions
    # ORM (vector embedding nullable, status_version).
    db.execute(
        text(
            """
            INSERT INTO source
              (id, url, canonical_url, title, publisher, version,
               date_publi, page, section, notes,
               captured_at, captured_by, verification_status,
               status_version, created_at, updated_at)
            VALUES
              (CAST(:id AS UUID), :url, :curl, :title, :pub, :ver,
               :dp, :page, :sec, :notes,
               now(), CAST(:cap AS UUID), 'pending',
               1, now(), now())
            """
        ),
        {
            "id": str(sid),
            "url": str(payload.url),
            "curl": canonical,
            "title": payload.title,
            "pub": payload.publisher,
            "ver": payload.version,
            "dp": payload.date_publi,
            "page": payload.page,
            "sec": payload.section,
            "notes": payload.notes,
            "cap": str(actor_id),
        },
    )

    # Audit append-only — ne doit jamais bloquer l'insertion principale.
    try:
        record_audit(
            db,
            entity_type="source",
            entity_id=sid,
            field=None,
            old=None,
            new={
                "url": str(payload.url),
                "canonical_url": canonical,
                "title": payload.title,
                "publisher": payload.publisher,
            },
            source_of_change="admin",
            user_id=actor_id,
        )
    except Exception:  # noqa: BLE001 — audit best-effort, jamais bloquant
        pass

    row = db.execute(
        text(
            "SELECT id, url, canonical_url, title, publisher, version, "
            "date_publi, page, section, captured_at, captured_by, "
            "verified_by, verified_at, verification_status, notes "
            "FROM source WHERE id = :id"
        ),
        {"id": str(sid)},
    ).mappings().first()
    return dict(row), head_warning  # type: ignore[arg-type]


__all__ = ["create_source", "find_duplicate", "ERROR_DUPLICATE"]
