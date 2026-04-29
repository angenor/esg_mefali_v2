"""F06 US6 — Catalog stats per entity (sidebar counters)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.registry import registry
from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin", tags=["admin-stats"])


@router.get("/stats/catalog", summary="Per-entity status counters")
def catalog_stats(
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for spec in registry.all():
        rows = db.execute(
            text(
                f"SELECT {spec.status_column} AS s, COUNT(*) AS c "  # noqa: S608
                f"FROM {spec.table} GROUP BY {spec.status_column}"
            )
        ).all()
        counters = {"draft": 0, "published": 0, "outdated": 0, "pending": 0}
        for r in rows:
            counters[r._mapping["s"]] = int(r._mapping["c"])
        out[spec.name] = counters
    return out
