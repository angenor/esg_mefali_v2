"""F20 — Admin Skills CRUD : router dédié /admin/skills/*.

Endpoints :
- GET    /admin/skills/                       — liste paginée + filtres
- POST   /admin/skills/                       — create draft
- GET    /admin/skills/{id}                   — read + ETag
- PUT    /admin/skills/{id}                   — update (draft in-place / published → new version)
- POST   /admin/skills/{id}/publish           — publish (sources verified + gating)
- POST   /admin/skills/{id}/run-eval          — eval golden examples (stub MVP)
- GET    /admin/skills/{id}/versions          — historique par `name`
- POST   /admin/skills/_estimate-tokens       — estimation len//4
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.audit import write_admin_event
from app.admin.deps import require_admin
from app.admin.etag import assert_version_match, make_etag, parse_if_match
from app.db import get_db
from app.models.account_user import AccountUser
from app.skills.evaluator import run_eval
from app.skills.fusion import SKILL_PROMPT_MAX_TOKENS
from app.skills.validation import (
    SKILL_GOLDEN_EXAMPLES_MIN,
    validate_skill_payload,
)

router = APIRouter(prefix="/admin/skills", tags=["admin-skills"])


_AUDIT_DIFF_FIELDS: tuple[str, ...] = (
    "name",
    "domain",
    "prompt_expert",
    "procedure",
    "tool_whitelist",
    "activation_rules",
    "golden_examples",
    "status",
    "version",
)


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping) if hasattr(row, "_mapping") else dict(row)


def _serialize(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, UUID):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _structured_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, dict[str, Any]] = {}
    for k in _AUDIT_DIFF_FIELDS:
        if before.get(k) != after.get(k):
            diff[k] = {"before": before.get(k), "after": after.get(k)}
    return {"sections": diff}


def _fetch_skill(db: Session, skill_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT * FROM skill WHERE id = CAST(:id AS UUID)"),
        {"id": skill_id},
    ).first()
    return _row_to_dict(row) if row else None


def _fetch_skill_sources(db: Session, skill_id: str) -> list[str]:
    rows = db.execute(
        text("SELECT source_id FROM skill_source WHERE skill_id = CAST(:id AS UUID)"),
        {"id": skill_id},
    ).all()
    return [str(r._mapping["source_id"]) for r in rows]


def _replace_skill_sources(db: Session, skill_id: str, source_ids: list[str]) -> None:
    db.execute(
        text("DELETE FROM skill_source WHERE skill_id = CAST(:id AS UUID)"),
        {"id": skill_id},
    )
    for sid in source_ids:
        db.execute(
            text(
                "INSERT INTO skill_source (skill_id, source_id) "
                "VALUES (CAST(:sk AS UUID), CAST(:sr AS UUID))"
            ),
            {"sk": skill_id, "sr": str(sid)},
        )


def _verify_sources_or_422(db: Session, source_ids: list[str]) -> None:
    if not source_ids:
        return
    rows = db.execute(
        text(
            "SELECT id, verification_status, title FROM source "
            "WHERE id = ANY(CAST(:ids AS UUID[]))"
        ),
        {"ids": [str(s) for s in source_ids]},
    ).all()
    found = {str(r._mapping["id"]): r._mapping for r in rows}
    missing: list[dict[str, Any]] = []
    for sid in source_ids:
        meta = found.get(str(sid))
        if not meta:
            missing.append({"id": str(sid), "status": "unknown", "label": "(introuvable)"})
        elif meta["verification_status"] != "verified":
            missing.append(
                {
                    "id": str(sid),
                    "status": meta["verification_status"],
                    "label": meta["title"] or "(sans titre)",
                }
            )
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "sources_not_verified",
                "missing_sources": missing,
                "message": f"{len(missing)} source(s) non verified.",
            },
        )


def _raise_validation_errors(report) -> None:  # type: ignore[no-untyped-def]
    if report.errors:
        primary = next(
            (e for e in report.errors if e["code"] == "prompt_injection_detected"),
            None,
        )
        code = primary["code"] if primary else "validation_failed"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": code,
                "message": "Validation échouée.",
                "errors": report.errors,
                "warnings": report.warnings,
            },
        )


def _pg_array(values: list[str]) -> str:
    safe = [v.replace('"', '\\"') for v in values]
    return "{" + ",".join(f'"{v}"' for v in safe) + "}"


@router.post("/_estimate-tokens", summary="Estimation len//4")
def estimate_tokens(
    payload: dict[str, Any] = Body(...),  # noqa: B008
    _: AccountUser = Depends(require_admin),
) -> dict[str, int]:
    text_in = payload.get("text", "") or ""
    return {"chars": len(text_in), "tokens": len(text_in) // 4}


@router.get("/", summary="List skills")
def list_skills(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
    domain: str | None = Query(None),
    db: Session = Depends(get_db),
    _: AccountUser = Depends(require_admin),
) -> dict[str, Any]:
    where: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status_filter:
        if status_filter not in {"draft", "published"}:
            raise HTTPException(status_code=400, detail={"code": "invalid_status"})
        where.append("status = :st")
        params["st"] = status_filter
    if domain:
        where.append("domain = :dom")
        params["dom"] = domain
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    rows = db.execute(
        text(
            f"""
            SELECT s.id, s.name, s.domain, s.version, s.status, s.created_by,
                   s.created_at, s.updated_at,
                   (SELECT COUNT(*) FROM skill_source ss
                    WHERE ss.skill_id = s.id) AS sources_count
            FROM skill s
            {where_sql}
            ORDER BY s.updated_at DESC, s.id DESC
            LIMIT :limit OFFSET :offset
            """  # noqa: S608
        ),
        params,
    ).all()
    items = [_serialize(_row_to_dict(r)) for r in rows]
    total = db.execute(
        text(f"SELECT COUNT(*) FROM skill {where_sql}"),  # noqa: S608
        {k: v for k, v in params.items() if k not in {"limit", "offset"}},
    ).scalar() or 0
    return {"items": items, "total": int(total), "limit": limit, "offset": offset}


@router.post("/", status_code=201, summary="Create draft skill")
def create_skill(
    response: Response,
    payload: dict[str, Any] = Body(...),  # noqa: B008
    db: Session = Depends(get_db),
    user: AccountUser = Depends(require_admin),
) -> dict[str, Any]:
    override = bool(payload.get("override_injection"))
    override_reason = payload.get("override_reason") or ""
    sources = list(payload.get("sources") or [])

    report = validate_skill_payload(payload, db, override_injection=override)
    _raise_validation_errors(report)

    tool_whitelist = list(payload.get("tool_whitelist") or [])
    activation_rules = payload.get("activation_rules") or {}
    golden_examples = payload.get("golden_examples") or []

    try:
        row = db.execute(
            text(
                """
                INSERT INTO skill (
                  name, version, domain, prompt_expert, procedure, tool_whitelist,
                  activation_rules, golden_examples, status, created_by,
                  created_at, updated_at
                ) VALUES (
                  :name, 1, :domain, :prompt_expert, :procedure,
                  CAST(:tool_whitelist AS TEXT[]),
                  CAST(:activation_rules AS JSONB),
                  CAST(:golden_examples AS JSONB),
                  'draft', CAST(:created_by AS UUID),
                  now(), now()
                ) RETURNING *
                """
            ),
            {
                "name": payload["name"].strip(),
                "domain": payload["domain"].strip(),
                "prompt_expert": payload["prompt_expert"],
                "procedure": payload.get("procedure") or "",
                "tool_whitelist": _pg_array(tool_whitelist),
                "activation_rules": json.dumps(activation_rules, ensure_ascii=False),
                "golden_examples": json.dumps(golden_examples, ensure_ascii=False),
                "created_by": str(user.id),
            },
        ).first()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=422, detail={"code": "insert_failed", "message": str(exc)}
        ) from exc
    obj = _row_to_dict(row)
    if sources:
        _replace_skill_sources(db, str(obj["id"]), sources)
    audit_after = _serialize(obj) | {"sources": sources}
    if override:
        audit_after["override_injection"] = True
        audit_after["override_reason"] = override_reason
    write_admin_event(
        db,
        user_id=user.id,
        entity_type="skill",
        entity_id=obj["id"],
        action="create",
        after=audit_after,
    )
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return _serialize(obj) | {"sources": sources, "warnings": report.warnings}


@router.get("/{skill_id}", summary="Read skill")
def get_skill(
    skill_id: str,
    response: Response,
    db: Session = Depends(get_db),
    _: AccountUser = Depends(require_admin),
) -> dict[str, Any]:
    obj = _fetch_skill(db, skill_id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    sources = _fetch_skill_sources(db, skill_id)
    response.headers["ETag"] = make_etag(obj["version"])
    return _serialize(obj) | {"sources": sources}


@router.put("/{skill_id}", summary="Update skill")
def update_skill(
    skill_id: str,
    response: Response,
    payload: dict[str, Any] = Body(...),  # noqa: B008
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(require_admin),
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = _fetch_skill(db, skill_id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))

    override = bool(payload.get("override_injection"))
    override_reason = payload.get("override_reason") or ""
    new_sources = list(payload.get("sources") or _fetch_skill_sources(db, skill_id))

    payload_for_validate = {
        "name": obj["name"],  # immutable
        "domain": payload.get("domain") or obj["domain"],
        "prompt_expert": payload.get("prompt_expert") or obj["prompt_expert"],
        "procedure": payload.get("procedure")
        if "procedure" in payload
        else obj.get("procedure", ""),
        "tool_whitelist": payload.get("tool_whitelist")
        if "tool_whitelist" in payload
        else (obj.get("tool_whitelist") or []),
        "activation_rules": payload.get("activation_rules")
        if "activation_rules" in payload
        else obj.get("activation_rules"),
        "golden_examples": payload.get("golden_examples")
        if "golden_examples" in payload
        else (obj.get("golden_examples") or []),
        "sources": new_sources,
    }
    report = validate_skill_payload(payload_for_validate, db, override_injection=override)
    _raise_validation_errors(report)

    tool_whitelist = list(payload_for_validate["tool_whitelist"] or [])
    activation_rules = payload_for_validate["activation_rules"] or {}
    golden_examples = payload_for_validate["golden_examples"] or []

    if obj["status"] == "draft":
        new_row = db.execute(
            text(
                """
                UPDATE skill SET
                  domain = :domain,
                  prompt_expert = :prompt_expert,
                  procedure = :procedure,
                  tool_whitelist = CAST(:tool_whitelist AS TEXT[]),
                  activation_rules = CAST(:activation_rules AS JSONB),
                  golden_examples = CAST(:golden_examples AS JSONB),
                  updated_at = now()
                WHERE id = CAST(:id AS UUID)
                RETURNING *
                """
            ),
            {
                "id": skill_id,
                "domain": payload_for_validate["domain"],
                "prompt_expert": payload_for_validate["prompt_expert"],
                "procedure": payload_for_validate["procedure"] or "",
                "tool_whitelist": _pg_array(tool_whitelist),
                "activation_rules": json.dumps(activation_rules, ensure_ascii=False),
                "golden_examples": json.dumps(golden_examples, ensure_ascii=False),
            },
        ).first()
        new_obj = _row_to_dict(new_row)
        _replace_skill_sources(db, skill_id, new_sources)
        diff = _structured_diff(_serialize(obj), _serialize(new_obj))
        write_admin_event(
            db,
            user_id=user.id,
            entity_type="skill",
            entity_id=new_obj["id"],
            action="update",
            before=_serialize(obj),
            after=_serialize(new_obj)
            | {
                "diff": diff,
                "sources": new_sources,
                "override_injection": override,
                "override_reason": override_reason,
            },
        )
        db.commit()
        response.headers["ETag"] = make_etag(new_obj["version"])
        return _serialize(new_obj) | {
            "sources": new_sources,
            "warnings": report.warnings,
        }

    # status == 'published' → new version draft.
    new_version = int(obj["version"]) + 1
    inserted = db.execute(
        text(
            """
            INSERT INTO skill (
              name, version, domain, prompt_expert, procedure, tool_whitelist,
              activation_rules, golden_examples, status, created_by,
              created_at, updated_at
            ) VALUES (
              :name, :version, :domain, :prompt_expert, :procedure,
              CAST(:tool_whitelist AS TEXT[]),
              CAST(:activation_rules AS JSONB),
              CAST(:golden_examples AS JSONB),
              'draft', CAST(:created_by AS UUID),
              now(), now()
            ) RETURNING *
            """
        ),
        {
            "name": obj["name"],
            "version": new_version,
            "domain": payload_for_validate["domain"],
            "prompt_expert": payload_for_validate["prompt_expert"],
            "procedure": payload_for_validate["procedure"] or "",
            "tool_whitelist": _pg_array(tool_whitelist),
            "activation_rules": json.dumps(activation_rules, ensure_ascii=False),
            "golden_examples": json.dumps(golden_examples, ensure_ascii=False),
            "created_by": str(user.id),
        },
    ).first()
    new_obj = _row_to_dict(inserted)
    _replace_skill_sources(db, str(new_obj["id"]), new_sources)
    write_admin_event(
        db,
        user_id=user.id,
        entity_type="skill",
        entity_id=new_obj["id"],
        action="new_version",
        before=_serialize(obj),
        after=_serialize(new_obj)
        | {"sources": new_sources, "from_version": obj["version"]},
    )
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return _serialize(new_obj) | {"sources": new_sources, "warnings": report.warnings}


@router.post("/{skill_id}/publish", summary="Publish skill")
def publish_skill(
    skill_id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    skip_eval_gating: bool = Header(False, alias="X-Skip-Eval-Gating"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(require_admin),
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = _fetch_skill(db, skill_id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    if obj["status"] == "published":
        raise HTTPException(
            status_code=409,
            detail={"code": "already_published", "message": "Déjà publié."},
        )

    sources = _fetch_skill_sources(db, skill_id)
    _verify_sources_or_422(db, sources)

    payload = {
        "name": obj["name"],
        "domain": obj["domain"],
        "prompt_expert": obj["prompt_expert"],
        "procedure": obj.get("procedure") or "",
        "tool_whitelist": obj.get("tool_whitelist") or [],
        "activation_rules": obj.get("activation_rules") or {},
        "golden_examples": obj.get("golden_examples") or [],
        "sources": sources,
    }
    report = validate_skill_payload(payload, db, for_publish=True)
    _raise_validation_errors(report)

    eval_report = run_eval(
        list(obj.get("tool_whitelist") or []),
        list(obj.get("golden_examples") or []),
    )
    if not skip_eval_gating and not eval_report.gating_pass:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "eval_gating_failed",
                "message": "L'eval gating bloque la publication.",
                "eval": eval_report.as_dict(),
                "hint": "Header X-Skip-Eval-Gating: true pour forcer (loggé).",
            },
        )

    new_row = db.execute(
        text(
            """
            UPDATE skill SET
              status = 'published',
              verified_by = CAST(:uid AS UUID),
              valid_from = COALESCE(valid_from, now()),
              updated_at = now()
            WHERE id = CAST(:id AS UUID)
            RETURNING *
            """
        ),
        {"uid": str(user.id), "id": skill_id},
    ).first()
    new_obj = _row_to_dict(new_row)
    write_admin_event(
        db,
        user_id=user.id,
        entity_type="skill",
        entity_id=new_obj["id"],
        action="publish",
        before=_serialize(obj),
        after=_serialize(new_obj)
        | {
            "eval": eval_report.as_dict(),
            "eval_gating_skipped": bool(skip_eval_gating),
        },
    )
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return _serialize(new_obj) | {"eval": eval_report.as_dict()}


@router.post("/{skill_id}/run-eval", summary="Run eval golden examples")
def run_skill_eval(
    skill_id: str,
    db: Session = Depends(get_db),
    _: AccountUser = Depends(require_admin),
) -> dict[str, Any]:
    obj = _fetch_skill(db, skill_id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    report = run_eval(
        list(obj.get("tool_whitelist") or []),
        list(obj.get("golden_examples") or []),
    )
    return {
        "skill_id": str(obj["id"]),
        "version": obj["version"],
        "eval": report.as_dict(),
    }


@router.get("/{skill_id}/versions", summary="Versions par name")
def list_versions(
    skill_id: str,
    db: Session = Depends(get_db),
    _: AccountUser = Depends(require_admin),
) -> dict[str, Any]:
    obj = _fetch_skill(db, skill_id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    rows = db.execute(
        text(
            """
            SELECT id, name, version, status, valid_from, valid_to,
                   created_at, updated_at, created_by, verified_by
            FROM skill
            WHERE name = :name
            ORDER BY version DESC
            """
        ),
        {"name": obj["name"]},
    ).all()
    return {
        "name": obj["name"],
        "items": [_serialize(_row_to_dict(r)) for r in rows],
        "min_golden_examples": SKILL_GOLDEN_EXAMPLES_MIN,
        "prompt_max_tokens": SKILL_PROMPT_MAX_TOKENS,
    }


__all__ = ["router"]
