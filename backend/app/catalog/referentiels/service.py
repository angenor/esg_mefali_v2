"""F09 US2 — Service ``referentiel`` : CRUD + /full + helper get_referentiel."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.audit import write_admin_event
from app.admin.etag import assert_version_match, parse_if_match
from app.catalog.referentiels.schemas import (
    IndicateurAttach,
    ReferentielCreate,
    ReferentielUpdate,
)
from app.catalog.referentiels.validator import validate_for_publish

TABLE = "referentiel"
JUNCTION_SRC = "referentiel_source"
JUNCTION_IND = "referentiel_indicateur"


def fetch_one(db: Session, id_: str) -> dict[str, Any] | None:
    row = db.execute(
        text(f"SELECT * FROM {TABLE} WHERE id = CAST(:id AS UUID)"),  # noqa: S608
        {"id": id_},
    ).first()
    return dict(row._mapping) if row else None


def list_sources(db: Session, ref_id: str) -> list[uuid.UUID]:
    rows = db.execute(
        text(
            f"SELECT source_id FROM {JUNCTION_SRC} "  # noqa: S608
            "WHERE referentiel_id = CAST(:id AS UUID)"
        ),
        {"id": ref_id},
    ).all()
    return [r[0] for r in rows]


def _set_sources(db: Session, ref_id: str, source_ids: list[uuid.UUID]) -> None:
    db.execute(
        text(f"DELETE FROM {JUNCTION_SRC} WHERE referentiel_id = CAST(:id AS UUID)"),  # noqa: S608
        {"id": ref_id},
    )
    for sid in source_ids:
        db.execute(
            text(
                f"INSERT INTO {JUNCTION_SRC}(referentiel_id, source_id) "  # noqa: S608
                "VALUES (CAST(:r AS UUID), CAST(:s AS UUID))"
            ),
            {"r": ref_id, "s": str(sid)},
        )


def create_referentiel(
    db: Session, payload: ReferentielCreate, *, actor_id: uuid.UUID
) -> dict[str, Any]:
    body = {
        "code": payload.code,
        "name": payload.name,
        "publisher": payload.publisher,
        "type": payload.type,
        "formula_type": payload.formula_type,
        "formula_expression": payload.formula_expression,
        "status": "draft",
        "version": 1,
        "created_by": str(actor_id),
    }
    cols = list(body.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    sql = text(
        f"INSERT INTO {TABLE} ({', '.join(cols)}) "  # noqa: S608
        f"VALUES ({placeholders}) RETURNING *"
    )
    try:
        row = db.execute(sql, body).first()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc
    obj = dict(row._mapping)
    if payload.source_ids:
        _set_sources(db, str(obj["id"]), payload.source_ids)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=obj["id"],
        action="create",
        after={"id": str(obj["id"]), "code": obj["code"]},
    )
    return obj


def update_referentiel(
    db: Session,
    id_: str,
    payload: ReferentielUpdate,
    *,
    actor_id: uuid.UUID,
    if_match: str | None,
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))

    update: dict[str, Any] = {}
    for k in ("name", "publisher", "type", "formula_type", "formula_expression"):
        v = getattr(payload, k)
        if v is not None:
            update[k] = v
    if update:
        set_clause = ", ".join(f"{k} = :{k}" for k in update)
        update["id"] = id_
        sql = text(
            f"UPDATE {TABLE} SET {set_clause}, updated_at=now() "  # noqa: S608
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        )
        try:
            row = db.execute(sql, update).first()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            raise HTTPException(
                status_code=422, detail={"code": "validation_failed", "message": str(exc)}
            ) from exc
        obj = dict(row._mapping)
    if payload.source_ids is not None:
        _set_sources(db, id_, payload.source_ids)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=obj["id"],
        action="update",
        after={"id": str(obj["id"])},
    )
    return obj


def attach_indicateur(
    db: Session, ref_id: str, payload: IndicateurAttach, *, actor_id: uuid.UUID
) -> dict[str, Any]:
    sql = text(
        f"INSERT INTO {JUNCTION_IND}(referentiel_id, indicateur_id, poids, seuil_min, seuil_max, source_id) "  # noqa: S608
        "VALUES (CAST(:r AS UUID), CAST(:i AS UUID), :poids, :smin, :smax, CAST(:src AS UUID)) "
        "ON CONFLICT (referentiel_id, indicateur_id) DO UPDATE SET "
        "poids = EXCLUDED.poids, seuil_min = EXCLUDED.seuil_min, "
        "seuil_max = EXCLUDED.seuil_max, source_id = EXCLUDED.source_id "
        "RETURNING *"
    )
    try:
        row = db.execute(
            sql,
            {
                "r": ref_id,
                "i": str(payload.indicateur_id),
                "poids": payload.poids,
                "smin": payload.seuil_min,
                "smax": payload.seuil_max,
                "src": str(payload.source_id),
            },
        ).first()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=422, detail={"code": "validation_failed", "message": str(exc)}
        ) from exc
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=JUNCTION_IND,
        entity_id=ref_id,
        action="attach",
        after={"referentiel_id": ref_id, "indicateur_id": str(payload.indicateur_id)},
    )
    return dict(row._mapping)


def detach_indicateur(
    db: Session, ref_id: str, indicateur_id: str, *, actor_id: uuid.UUID
) -> None:
    db.execute(
        text(
            f"DELETE FROM {JUNCTION_IND} "  # noqa: S608
            "WHERE referentiel_id = CAST(:r AS UUID) AND indicateur_id = CAST(:i AS UUID)"
        ),
        {"r": ref_id, "i": indicateur_id},
    )
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=JUNCTION_IND,
        entity_id=ref_id,
        action="detach",
        after={"referentiel_id": ref_id, "indicateur_id": indicateur_id},
    )


def get_full(db: Session, ref_id: str) -> dict[str, Any] | None:
    """FR-003 — payload joint complet (référentiel + indicateurs liés + sources)."""
    obj = fetch_one(db, ref_id)
    if not obj:
        return None
    out = dict(obj)
    out["indicateurs"] = [
        dict(r._mapping)
        for r in db.execute(
            text(
                "SELECT i.id, i.code, i.name, i.pillar, i.unite, i.value_type, i.status, "
                "ri.poids, ri.seuil_min, ri.seuil_max, ri.source_id "
                "FROM indicateur i "
                f"JOIN {JUNCTION_IND} ri ON ri.indicateur_id = i.id "
                "WHERE ri.referentiel_id = CAST(:id AS UUID) "
                "ORDER BY ri.poids DESC, i.code"
            ),
            {"id": ref_id},
        ).all()
    ]
    out["sources"] = [
        dict(r._mapping)
        for r in db.execute(
            text(
                "SELECT s.id, s.title, s.publisher, s.url, s.verification_status "
                "FROM source s "
                f"JOIN {JUNCTION_SRC} rs ON rs.source_id = s.id "
                "WHERE rs.referentiel_id = CAST(:id AS UUID)"
            ),
            {"id": ref_id},
        ).all()
    ]
    return out


def publish_referentiel(
    db: Session, id_: str, *, actor_id: uuid.UUID, if_match: str | None
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    if obj["status"] == "published":
        raise HTTPException(
            status_code=409,
            detail={"code": "already_published", "message": "Déjà publié."},
        )
    failures = validate_for_publish(db, id_)
    if failures:
        raise HTTPException(
            status_code=409,
            detail={"code": "validation_failed", "failures": failures},
        )
    row = db.execute(
        text(
            f"UPDATE {TABLE} SET status='published', "  # noqa: S608
            f"published_by = CAST(:uid AS UUID), updated_at=now() "
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        ),
        {"uid": str(actor_id), "id": id_},
    ).first()
    new_obj = dict(row._mapping)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=new_obj["id"],
        action="publish",
        after={"id": str(new_obj["id"]), "version": new_obj["version"]},
    )
    return new_obj


def archive_referentiel(
    db: Session, id_: str, *, actor_id: uuid.UUID, if_match: str | None
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    row = db.execute(
        text(
            f"UPDATE {TABLE} SET status='archived', updated_at=now() "  # noqa: S608
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        ),
        {"id": id_},
    ).first()
    new_obj = dict(row._mapping)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=new_obj["id"],
        action="archive",
        after={"id": str(new_obj["id"])},
    )
    return new_obj


def list_referentiels(
    db: Session,
    *,
    type_: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    where: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if type_:
        where.append("type = :type")
        params["type"] = type_
    if status_filter:
        where.append("status = :status")
        params["status"] = status_filter
    if search:
        where.append("(code ILIKE :q OR name ILIKE :q)")
        params["q"] = f"%{search}%"
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"SELECT * FROM {TABLE} {where_sql} "  # noqa: S608
        f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    )
    rows = [dict(r._mapping) for r in db.execute(sql, params).all()]
    total = db.execute(
        text(f"SELECT count(*) FROM {TABLE} {where_sql}"),  # noqa: S608
        {k: v for k, v in params.items() if k not in {"limit", "offset"}},
    ).scalar() or 0
    return {"items": rows, "total": int(total), "limit": limit, "offset": offset}


def get_referentiel(
    db: Session, code: str, version: int | None = None
) -> dict[str, Any] | None:
    """FR-008 helper consommable par F23/F28.

    Si ``version`` non fourni : retourne la version ``published`` la plus récente.
    """
    if version is None:
        sql = text(
            "SELECT * FROM referentiel WHERE code = :code AND status = 'published' "
            "ORDER BY version DESC LIMIT 1"
        )
        row = db.execute(sql, {"code": code}).first()
    else:
        sql = text("SELECT * FROM referentiel WHERE code = :code AND version = :v LIMIT 1")
        row = db.execute(sql, {"code": code, "v": version}).first()
    return dict(row._mapping) if row else None
