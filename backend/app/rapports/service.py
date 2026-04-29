"""F24 — Service de génération de rapports PDF.

Orchestration : lecture des scores (F23) -> assemblage du payload ->
rendu PDF (reportlab) -> persistance disque + DB -> audit (F04).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.config import get_settings
from app.entreprise.service import get_or_provision_entreprise
from app.rapports.pdf_builder import (
    IndicatorEntry,
    RapportPayload,
    ReferentielSection,
    build_pdf,
)
from app.scoring.service import (
    EntityNotAccessible,
    ReferentielNotFound,
    compute_and_persist,
    get_latest_score_detail,
)
from app.utils.sources_appendix import build_sources_appendix

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------


def _resolve_entreprise_name(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
) -> str:
    """Récupère le nom de la PME pour la couverture du rapport."""
    ent = get_or_provision_entreprise(db, account_id=account_id)
    return ent.name or "Entreprise (sans nom)"


def _ensure_score(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    referentiel_code: str,
    user_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Renvoie le dernier score persisté, ou en calcule un si absent."""
    detail = get_latest_score_detail(
        db,
        account_id=account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        referentiel_code=referentiel_code,
    )
    if detail is not None:
        return detail
    return compute_and_persist(
        db,
        account_id=account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        referentiel_code=referentiel_code,
        user_id=user_id,
    )


def _split_points_lacunes(
    detail: Mapping[str, Any],
) -> tuple[list[IndicatorEntry], list[IndicatorEntry]]:
    """Heuristique MVP : point fort = contribution >= 50 ; lacune = manquant."""
    points: list[IndicatorEntry] = []
    for c in detail.get("indicateurs_couverts", []) or []:
        try:
            contrib = (
                float(c.get("contribution"))
                if c.get("contribution") is not None
                else None
            )
        except (TypeError, ValueError):
            contrib = None
        if contrib is not None and contrib >= 50:
            points.append(
                IndicatorEntry(
                    code=str(c.get("indicateur_code") or ""),
                    pillar=str(c.get("pillar") or ""),
                    contribution=contrib,
                )
            )
    lacunes: list[IndicatorEntry] = []
    for m in detail.get("indicateurs_manquants", []) or []:
        lacunes.append(
            IndicatorEntry(
                code=str(m.get("indicateur_code") or ""),
                pillar=str(m.get("pillar") or ""),
                reason=str(m.get("reason") or ""),
            )
        )
    return points, lacunes


def _collect_source_ids(details: list[Mapping[str, Any]]) -> list[uuid.UUID]:
    seen: set[str] = set()
    out: list[uuid.UUID] = []
    for d in details:
        for s in d.get("sources_used", []) or []:
            sid = str(s)
            if sid in seen:
                continue
            seen.add(sid)
            try:
                out.append(uuid.UUID(sid))
            except (TypeError, ValueError):
                continue
    return out


def _serialize_snapshot(details: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Snapshot reproductible (versioning F04) — taillé pour JSONB."""
    safe: list[dict[str, Any]] = []
    for d in details:
        safe.append(
            {
                "referentiel_code": d.get("referentiel_code"),
                "referentiel_version": int(d.get("referentiel_version") or 0),
                "score_global": (
                    float(d["score_global"])
                    if d.get("score_global") is not None
                    else None
                ),
                "scores_by_pillar": dict(d.get("scores_by_pillar") or {}),
                "coverage_ratio": (
                    float(d["coverage_ratio"])
                    if d.get("coverage_ratio") is not None
                    else None
                ),
                "computed_at": (
                    d["computed_at"].isoformat()
                    if isinstance(d.get("computed_at"), datetime)
                    else d.get("computed_at")
                ),
            }
        )
    return {"sections": safe}


def _storage_path(account_id: uuid.UUID, rapport_id: uuid.UUID) -> Path:
    base = Path(get_settings().RAPPORT_STORAGE_DIR)
    return base / str(account_id) / f"{rapport_id}.pdf"


# -----------------------------------------------------------------
# Public API
# -----------------------------------------------------------------


def generate_rapport(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    referentiels: list[str],
    language: str = "fr",
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Génère un rapport PDF, persiste sur disque + en DB, audit append-only."""
    if entity_type not in {"entreprise", "projet"}:
        raise ValueError(f"entity_type invalide: {entity_type}")
    if not referentiels:
        raise ValueError("au moins un référentiel est requis")

    entreprise_name = _resolve_entreprise_name(
        db,
        account_id=account_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    details: list[dict[str, Any]] = []
    for code in referentiels:
        try:
            d = _ensure_score(
                db,
                account_id=account_id,
                entity_type=entity_type,
                entity_id=entity_id,
                referentiel_code=code,
                user_id=user_id,
            )
        except ReferentielNotFound:
            logger.warning("rapport.referentiel_not_found code=%s", code)
            continue
        except EntityNotAccessible:
            logger.warning(
                "rapport.entity_not_accessible entity_id=%s", entity_id
            )
            raise
        details.append(d)

    sections: list[ReferentielSection] = []
    for d in details:
        points, lacunes = _split_points_lacunes(d)
        sections.append(
            ReferentielSection(
                code=str(d.get("referentiel_code") or ""),
                version=int(d.get("referentiel_version") or 0),
                score_global=(
                    float(d["score_global"])
                    if d.get("score_global") is not None
                    else None
                ),
                coverage_ratio=(
                    float(d["coverage_ratio"])
                    if d.get("coverage_ratio") is not None
                    else None
                ),
                scores_by_pillar=dict(d.get("scores_by_pillar") or {}),
                points_forts=points,
                lacunes=lacunes,
            )
        )

    source_ids = _collect_source_ids(details)
    appendix_md = build_sources_appendix(db, source_ids)

    rapport_id = uuid.uuid4()
    generated_at = datetime.now(UTC)

    payload = RapportPayload(
        rapport_id=rapport_id,
        entreprise_name=entreprise_name,
        generated_at=generated_at,
        language=language,
        sections=sections,
        sources_appendix_md=appendix_md,
    )

    pdf_bytes = build_pdf(payload)

    file_path = _storage_path(account_id, rapport_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(pdf_bytes)

    snapshot = _serialize_snapshot(details)
    db.execute(
        text(
            """
            INSERT INTO rapport_genere (
              id, account_id, entity_type, entity_id,
              referentiels, language, file_path, file_size_bytes,
              score_snapshot_json, generated_at, generated_by
            ) VALUES (
              CAST(:id AS UUID), CAST(:aid AS UUID), :etype, CAST(:eid AS UUID),
              CAST(:refs AS TEXT[]), :lang, :path, :size,
              CAST(:snapshot AS JSONB), :gat, CAST(:uid AS UUID)
            )
            """
        ),
        {
            "id": str(rapport_id),
            "aid": str(account_id),
            "etype": entity_type,
            "eid": str(entity_id),
            "refs": referentiels,
            "lang": language,
            "path": str(file_path),
            "size": len(pdf_bytes),
            "snapshot": json.dumps(snapshot),
            "gat": generated_at,
            "uid": str(user_id) if user_id else None,
        },
    )

    record_audit(
        db,
        entity_type="rapport_genere",
        entity_id=rapport_id,
        field="generate",
        new={
            "referentiels": referentiels,
            "language": language,
            "file_size_bytes": len(pdf_bytes),
            "sections_count": len(sections),
        },
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )

    return {
        "rapport_id": rapport_id,
        "account_id": account_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "referentiels": list(referentiels),
        "language": language,
        "file_path": str(file_path),
        "file_size_bytes": len(pdf_bytes),
        "generated_at": generated_at,
        "score_snapshot": snapshot,
    }


def list_rapports(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    where = ["account_id = CAST(:aid AS UUID)"]
    params: dict[str, Any] = {"aid": str(account_id), "limit": int(limit)}
    if entity_type:
        where.append("entity_type = :etype")
        params["etype"] = entity_type
    if entity_id:
        where.append("entity_id = CAST(:eid AS UUID)")
        params["eid"] = str(entity_id)
    sql = (
        "SELECT id, entity_type, entity_id, referentiels, language, "
        "file_size_bytes, generated_at FROM rapport_genere WHERE "
        + " AND ".join(where)
        + " ORDER BY generated_at DESC LIMIT :limit"
    )
    rows = db.execute(text(sql), params).fetchall()
    return [
        {
            "rapport_id": r.id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "referentiels": list(r.referentiels or []),
            "language": r.language,
            "file_size_bytes": r.file_size_bytes,
            "generated_at": r.generated_at,
        }
        for r in rows
    ]


def get_rapport(
    db: Session,
    *,
    account_id: uuid.UUID,
    rapport_id: uuid.UUID,
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, entity_type, entity_id, referentiels, language,
                   file_path, file_size_bytes, generated_at, score_snapshot_json
            FROM rapport_genere
            WHERE id = CAST(:id AS UUID) AND account_id = CAST(:aid AS UUID)
            """
        ),
        {"id": str(rapport_id), "aid": str(account_id)},
    ).first()
    if row is None:
        return None
    return {
        "rapport_id": row.id,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "referentiels": list(row.referentiels or []),
        "language": row.language,
        "file_path": row.file_path,
        "file_size_bytes": row.file_size_bytes,
        "generated_at": row.generated_at,
        "score_snapshot": dict(row.score_snapshot_json or {}),
    }


__all__ = [
    "generate_rapport",
    "list_rapports",
    "get_rapport",
    "_storage_path",
    "_split_points_lacunes",
    "_collect_source_ids",
    "_serialize_snapshot",
]
