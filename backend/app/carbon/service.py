"""F28 - Service Carbone (orchestrateur lookup F09 + engine + persist + audit)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit import SourceOfChange, record_audit
from app.carbon.engine import BreakdownLine, FactorRef, compute_line, compute_total
from app.carbon.plan import generate_plan as build_reduction_plan
from app.carbon.schemas import CarbonComputeRequest


class FactorNotFound(Exception):
    """Facteur F09 absent pour le code (pays/year) demande."""


class FootprintNotFound(Exception):
    """Aucune empreinte calculee pour cette annee."""


def _resolve_factor(
    db: Session, code: str, pays_iso2: str | None, year: int
) -> FactorRef:
    from app.catalog.facteurs_emission.lookup import get_facteur

    at = date(year, 12, 31)
    row = get_facteur(db, code, pays_iso2=pays_iso2, at=at)
    if row is None:
        raise FactorNotFound(
            f"facteur introuvable: code={code} pays={pays_iso2} year={year}"
        )
    return FactorRef(
        factor_id=str(row["id"]),
        code=row["code"],
        valeur=Decimal(row["valeur"]),
        unite=row["unite"],
        scope=str(row["scope"]),
        categorie=row.get("categorie") or "autre",
        source_id=str(row["source_id"]),
        version=int(row["version"]),
    )


def compute_footprint(
    db: Session,
    *,
    account_id: UUID,
    entreprise_id: UUID | None,
    user_id: UUID | None,
    request: CarbonComputeRequest,
    default_country: str | None = None,
) -> dict[str, Any]:
    """Resout chaque poste -> calcule -> persiste -> audit."""
    lines: list[BreakdownLine] = []
    factor_versions: list[dict[str, Any]] = []

    for item in request.source_data:
        country = item.country or default_country
        factor = _resolve_factor(db, item.code, country, request.year)
        line = compute_line(item.quantity, factor)
        lines.append(line)
        factor_versions.append(
            {
                "code": factor.code,
                "factor_id": factor.factor_id,
                "version": factor.version,
                "source_id": factor.source_id,
                "country": country,
            }
        )

    totals = compute_total(lines)
    breakdown_json = [
        {
            "code": ln.code,
            "quantity": str(ln.quantity),
            "unit": ln.unit,
            "factor_id": ln.factor.factor_id,
            "factor_value": str(ln.factor.valeur),
            "factor_source_id": ln.factor.source_id,
            "factor_version": ln.factor.version,
            "scope": ln.factor.scope,
            "categorie": ln.factor.categorie,
            "kgco2e": str(ln.kgco2e),
        }
        for ln in lines
    ]

    by_scope_str = {k: str(v) for k, v in totals["by_scope_kgco2e"].items()}
    new_id = uuid.uuid4()
    now = datetime.now(UTC)
    db.execute(
        text(
            """
            INSERT INTO carbon_footprint (
                id, account_id, entreprise_id, year,
                source_data_json, total_tco2e, by_scope_json, breakdown_json,
                factor_versions_json, computed_at, version
            ) VALUES (
                CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:eid AS UUID), :year,
                CAST(:sd AS JSONB), :total, CAST(:bs AS JSONB), CAST(:bd AS JSONB),
                CAST(:fv AS JSONB), :ca, :ver
            )
            """
        ),
        {
            "id": str(new_id),
            "aid": str(account_id),
            "eid": str(entreprise_id) if entreprise_id else None,
            "year": request.year,
            "sd": json.dumps(
                {"items": [item.model_dump(mode="json") for item in request.source_data]}
            ),
            "total": str(totals["total_tco2e"]),
            "bs": json.dumps(by_scope_str),
            "bd": json.dumps(breakdown_json),
            "fv": json.dumps(factor_versions),
            "ca": now,
            "ver": 1,
        },
    )

    record_audit(
        db,
        entity_type="carbon_footprint",
        entity_id=new_id,
        field="compute",
        new={
            "year": request.year,
            "total_tco2e": str(totals["total_tco2e"]),
            "items": len(request.source_data),
        },
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )

    return {
        "id": new_id,
        "year": request.year,
        "total_tco2e": totals["total_tco2e"],
        "by_scope_kgco2e": totals["by_scope_kgco2e"],
        "by_category_kgco2e": totals["by_category_kgco2e"],
        "breakdown": breakdown_json,
        "factor_versions": factor_versions,
    }


def get_latest(db: Session, *, account_id: UUID, year: int) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, year, total_tco2e, by_scope_json, breakdown_json,
                   factor_versions_json
            FROM carbon_footprint
            WHERE account_id = CAST(:aid AS UUID) AND year = :year
            ORDER BY computed_at DESC LIMIT 1
            """
        ),
        {"aid": str(account_id), "year": year},
    ).first()
    if row is None:
        raise FootprintNotFound(f"no carbon_footprint for year={year}")
    m = row._mapping
    by_scope = m["by_scope_json"] or {}
    by_category: dict[str, Decimal] = {}
    for ln in m["breakdown_json"] or []:
        cat = ln.get("categorie") or "autre"
        by_category[cat] = by_category.get(cat, Decimal("0")) + Decimal(
            ln.get("kgco2e", "0")
        )
    return {
        "id": m["id"],
        "year": m["year"],
        "total_tco2e": Decimal(m["total_tco2e"]),
        "by_scope_kgco2e": {k: Decimal(v) for k, v in by_scope.items()},
        "by_category_kgco2e": by_category,
        "breakdown": m["breakdown_json"] or [],
        "factor_versions": m["factor_versions_json"] or [],
    }


def reduction_plan(db: Session, *, account_id: UUID, year: int) -> dict[str, Any]:
    latest = get_latest(db, account_id=account_id, year=year)
    actions = build_reduction_plan(latest["by_category_kgco2e"])
    for a in actions:
        if isinstance(a.get("impact_kgco2e_year"), Decimal):
            a["impact_kgco2e_year"] = str(a["impact_kgco2e_year"])
    return {"year": year, "actions": actions}
