"""F28 + F47 - Service Carbone.

Orchestrateur lookup F09 + engine + persist + audit.

F47 ajoute :
- ``list_index`` : index multi-année (lecture seule).
- ``recompute`` : rejoue compute_footprint avec source_data figé.
- ``edit_line`` : reconstruit source_data + remplace/ajoute ligne + recompute.
- ``_assert_source_verified`` : helper P1 pour edit-line.
- ``SourceNotVerified`` : exception dédiée.
"""

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
from app.carbon.schemas import (
    CarbonComputeRequest,
    CarbonEditLineRequest,
    CarbonSourceItem,
)


class FactorNotFound(Exception):
    """Facteur F09 absent pour le code (pays/year) demande."""


class FootprintNotFound(Exception):
    """Aucune empreinte calculee pour cette annee."""


class SourceNotVerified(Exception):
    """Source absente, autre tenant, ou statut != 'verified' (F47 P1)."""


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
    forced_version: int | None = None,
) -> dict[str, Any]:
    """Resout chaque poste -> calcule -> persiste -> audit.

    F47 : ``forced_version`` permet à recompute/edit_line de propager le
    nouveau numéro de version (max(prev)+1) sans relire la base.
    """
    lines: list[BreakdownLine] = []
    factor_versions: list[dict[str, Any]] = []
    breakdown_source_ids: list[str | None] = []

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
        breakdown_source_ids.append(
            str(item.source_id) if item.source_id is not None else None
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
            "source_id": breakdown_source_ids[idx],
        }
        for idx, ln in enumerate(lines)
    ]

    by_scope_str = {k: str(v) for k, v in totals["by_scope_kgco2e"].items()}
    new_id = uuid.uuid4()
    now = datetime.now(UTC)
    version = forced_version if forced_version is not None else 1
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
            "ver": version,
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
        "version": version,
        "computed_at": now,
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


def _load_latest_full(
    db: Session, *, account_id: UUID, year: int
) -> dict[str, Any]:
    """Variante interne F47 : retourne aussi computed_at, version,
    source_data_json, entreprise_id (nécessaires à recompute/edit_line)."""
    row = db.execute(
        text(
            """
            SELECT id, year, total_tco2e, by_scope_json, breakdown_json,
                   factor_versions_json, computed_at, version, source_data_json,
                   entreprise_id
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
    return {
        "id": m["id"],
        "year": m["year"],
        "total_tco2e": Decimal(m["total_tco2e"]),
        "computed_at": m["computed_at"],
        "version": int(m["version"]) if m["version"] is not None else 1,
        "source_data_json": m["source_data_json"] or {"items": []},
        "entreprise_id": m["entreprise_id"],
    }


def reduction_plan(db: Session, *, account_id: UUID, year: int) -> dict[str, Any]:
    latest = get_latest(db, account_id=account_id, year=year)
    actions = build_reduction_plan(latest["by_category_kgco2e"])
    for a in actions:
        if isinstance(a.get("impact_kgco2e_year"), Decimal):
            a["impact_kgco2e_year"] = str(a["impact_kgco2e_year"])
    return {"year": year, "actions": actions}


# =====================================================================
# F47 — list_index, recompute, edit_line, _assert_source_verified
# =====================================================================


def list_index(
    db: Session, *, account_id: UUID, limit_years: int = 10
) -> list[dict[str, Any]]:
    """Index multi-année : la dernière empreinte par year, triée desc.

    Lecture seule, RLS-aware via account_id, pas d'audit.
    """
    rows = db.execute(
        text(
            """
            SELECT DISTINCT ON (year) id, year, total_tco2e, computed_at, version
            FROM carbon_footprint
            WHERE account_id = CAST(:aid AS UUID)
            ORDER BY year DESC, computed_at DESC
            LIMIT :limit
            """
        ),
        {"aid": str(account_id), "limit": int(limit_years)},
    ).fetchall()
    return [
        {
            "footprint_id": r._mapping["id"],
            "year": int(r._mapping["year"]),
            "total_tco2e": Decimal(r._mapping["total_tco2e"]),
            "computed_at": r._mapping["computed_at"],
            "version": int(r._mapping["version"]),
        }
        for r in rows
    ]


def _items_from_source_data_json(source_data_json: Any) -> list[dict[str, Any]]:
    """Extrait la liste d'items du JSONB ``source_data_json``.

    Forme attendue : ``{"items": [...]}``. Tolère aussi la liste brute pour
    rétrocompat éventuelle.
    """
    if isinstance(source_data_json, dict):
        items = source_data_json.get("items") or []
    elif isinstance(source_data_json, list):
        items = source_data_json
    else:
        items = []
    return [dict(it) for it in items]


def recompute(
    db: Session,
    *,
    account_id: UUID,
    year: int,
    user_id: UUID | None,
) -> dict[str, Any]:
    """Rejoue compute_footprint sur la dernière empreinte de l'année.

    F47 US5. Crée une nouvelle row carbon_footprint (append-only) avec
    ``version = previous.version + 1``. Audit ``field="recompute"``.
    """
    previous = _load_latest_full(db, account_id=account_id, year=year)
    items = _items_from_source_data_json(previous["source_data_json"])
    if not items:
        # Edge case : empreinte historique vide → rien à recalculer.
        raise FootprintNotFound(f"empty source_data for year={year}")

    request = CarbonComputeRequest(
        year=year,
        source_data=[CarbonSourceItem(**item) for item in items],
    )
    next_version = int(previous["version"] or 1) + 1
    new_result = compute_footprint(
        db,
        account_id=account_id,
        entreprise_id=previous.get("entreprise_id"),
        user_id=user_id,
        request=request,
        forced_version=next_version,
    )
    record_audit(
        db,
        entity_type="carbon_footprint",
        entity_id=new_result["id"],
        field="recompute",
        old={
            "footprint_id": str(previous["id"]),
            "total_tco2e": str(previous["total_tco2e"]),
        },
        new={
            "footprint_id": str(new_result["id"]),
            "total_tco2e": str(new_result["total_tco2e"]),
        },
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )
    return {**new_result, "previous_footprint_id": previous["id"]}


def _assert_source_verified(
    db: Session, *, source_id: UUID, account_id: UUID
) -> None:
    """Vérifie que la Source existe, appartient au tenant, et est ``verified``.

    Lève ``SourceNotVerified`` sinon. Hypothèse table ``source`` avec colonnes
    (id, account_id, statut). Si la table porte un autre nom, ce helper sera
    le seul point à adapter.
    """
    row = db.execute(
        text(
            """
            SELECT statut FROM source
            WHERE id = CAST(:sid AS UUID) AND account_id = CAST(:aid AS UUID)
            """
        ),
        {"sid": str(source_id), "aid": str(account_id)},
    ).first()
    if row is None:
        raise SourceNotVerified(
            f"source {source_id} introuvable ou autre tenant"
        )
    statut = row._mapping["statut"]
    if str(statut) != "verified":
        raise SourceNotVerified(
            f"source {source_id} statut={statut!r} (attendu 'verified')"
        )


def edit_line(
    db: Session,
    *,
    account_id: UUID,
    year: int,
    user_id: UUID | None,
    payload: CarbonEditLineRequest,
) -> dict[str, Any]:
    """Modifie ou ajoute une ligne d'activité, recalcule l'empreinte.

    F47 US3. Source obligatoire et vérifiée (P1). Append-only (P3/P4).
    """
    _assert_source_verified(
        db, source_id=payload.source_id, account_id=account_id
    )
    previous = _load_latest_full(db, account_id=account_id, year=year)
    items = _items_from_source_data_json(previous["source_data_json"])
    new_item = {
        "code": payload.code,
        "quantity": str(payload.quantity),
        "country": payload.country,
        "source_id": str(payload.source_id),
    }
    found_idx = next(
        (i for i, it in enumerate(items) if it.get("code") == payload.code),
        None,
    )
    old_payload: dict[str, Any] = {"code": payload.code, "quantity": None, "source_id": None}
    if found_idx is not None:
        old_payload = {
            "code": payload.code,
            "quantity": items[found_idx].get("quantity"),
            "source_id": items[found_idx].get("source_id"),
        }
        items[found_idx] = new_item
    else:
        items.append(new_item)

    request = CarbonComputeRequest(
        year=year,
        source_data=[CarbonSourceItem(**it) for it in items],
    )
    next_version = int(previous["version"] or 1) + 1
    new_result = compute_footprint(
        db,
        account_id=account_id,
        entreprise_id=previous.get("entreprise_id"),
        user_id=user_id,
        request=request,
        forced_version=next_version,
    )
    record_audit(
        db,
        entity_type="carbon_footprint",
        entity_id=new_result["id"],
        field="edit-line",
        old=old_payload,
        new={
            "code": payload.code,
            "quantity": str(payload.quantity),
            "source_id": str(payload.source_id),
            "country": payload.country,
        },
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )
    return {
        **new_result,
        "previous_footprint_id": previous["id"],
        "edited_line_code": payload.code,
    }
