"""F06 US5 — Global admin search across all registered entities (P2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.crud_router import _serialize
from app.admin.registry import registry
from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin", tags=["admin-search"])


@router.get("/search", summary="Global catalog search")
def search(
    q: str = Query(..., min_length=2),
    types: str | None = Query(None, description="Comma-separated entity names"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    if len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail={"code": "q_too_short"})
    selected = (
        {t.strip() for t in types.split(",") if t.strip()} if types else None
    )

    groups: list[dict[str, Any]] = []
    for spec in registry.all():
        if selected and spec.name not in selected:
            continue
        if not spec.searchable_fields:
            continue
        # Build OR clause across searchable fields.
        sim_expr = " + ".join(
            f"COALESCE(similarity({f}, :q), 0)" for f in spec.searchable_fields
        )
        ilike_clauses = " OR ".join(
            f"{f} ILIKE :ql" for f in spec.searchable_fields
        )
        sql = text(
            f"""
            SELECT id, name, publisher, external_id, status,
                   ({sim_expr}) AS similarity
            FROM {spec.table}
            WHERE {ilike_clauses}
            ORDER BY similarity DESC, name ASC
            LIMIT 10
            """  # noqa: S608
        )
        rows = db.execute(sql, {"q": q, "ql": f"%{q}%"}).all()
        items = [_serialize(dict(r._mapping)) for r in rows]
        groups.append({"entity": spec.name, "items": items})
    return {"query": q, "groups": groups}
