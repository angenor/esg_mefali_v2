"""F12 - Service projets : CRUD + duplicate + transition + audit + versioning.

Aligne sur le pattern F11 (entreprise/service.py).
"""

from __future__ import annotations

import json as _json
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.projets.events import publish_sync
from app.projets.validators import (
    validate_indicateurs,
    validate_maturite,
    validate_statut,
    validate_structure_financement,
    validate_types_impact,
)


class VersionConflict(Exception):
    def __init__(self, current_version: int, your_version: int) -> None:
        self.current_version = current_version
        self.your_version = your_version
        super().__init__(
            f"version conflict (current={current_version}, your={your_version})"
        )


class ProjetNotFound(Exception):
    pass


class DeleteProtected(Exception):
    """Suppression d'un projet finance/en_execution sans X-Confirm."""

    def __init__(self, statut: str) -> None:
        self.statut = statut
        super().__init__(
            f"Projet en statut '{statut}' : header X-Confirm: true requis pour supprimer."
        )


@dataclass(frozen=True)
class ProjetRow:
    id: UUID
    account_id: UUID
    entreprise_id: UUID
    version: int
    nom: str
    description: str | None
    objectif_environnemental: str | None
    types_impact: list[str] | None
    maturite: str | None
    montant_recherche_amount: Decimal | None
    montant_recherche_currency: str | None
    duree_mois: int | None
    structure_financement_arr: list[str] | None
    indicateurs_impact_json: list[dict[str, Any]] | None
    localisation_pays_iso2: str | None
    localisation_ville: str | None
    statut: str | None
    created_at: datetime | None
    updated_at: datetime | None


_SELECT_COLS = """
    id, account_id, entreprise_id, version, nom, description,
    objectif_environnemental, types_impact, maturite,
    montant_recherche_amount, montant_recherche_currency,
    duree_mois, structure_financement_arr,
    indicateurs_impact_json,
    localisation_pays_iso2, localisation_ville,
    statut, created_at, updated_at
"""


def _row_to_dataclass(r: Any) -> ProjetRow:
    return ProjetRow(
        id=r.id,
        account_id=r.account_id,
        entreprise_id=r.entreprise_id,
        version=int(r.version),
        nom=r.nom,
        description=r.description,
        objectif_environnemental=r.objectif_environnemental,
        types_impact=list(r.types_impact) if r.types_impact is not None else None,
        maturite=r.maturite,
        montant_recherche_amount=r.montant_recherche_amount,
        montant_recherche_currency=r.montant_recherche_currency,
        duree_mois=int(r.duree_mois) if r.duree_mois is not None else None,
        structure_financement_arr=(
            list(r.structure_financement_arr)
            if r.structure_financement_arr is not None
            else None
        ),
        indicateurs_impact_json=r.indicateurs_impact_json,
        localisation_pays_iso2=(
            r.localisation_pays_iso2.strip()
            if r.localisation_pays_iso2 else None
        ),
        localisation_ville=r.localisation_ville,
        statut=r.statut,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _select_one(db: Session, *, projet_id: UUID | str, account_id: UUID | str) -> ProjetRow | None:
    sql = text(
        f"""
        SELECT {_SELECT_COLS}
        FROM projet
        WHERE id = CAST(:pid AS UUID)
          AND account_id = CAST(:aid AS UUID)
          AND deleted_at IS NULL
        LIMIT 1
        """
    )
    row = db.execute(sql, {"pid": str(projet_id), "aid": str(account_id)}).first()
    return _row_to_dataclass(row) if row is not None else None


def _entreprise_id(db: Session, account_id: UUID | str) -> UUID:
    row = db.execute(
        text(
            "SELECT id FROM entreprise WHERE account_id = CAST(:aid AS UUID) "
            "AND deleted_at IS NULL LIMIT 1"
        ),
        {"aid": str(account_id)},
    ).first()
    if row is None:
        raise RuntimeError("Profil entreprise inexistant. GET /me/entreprise d'abord.")
    return row[0]


def list_projets(
    db: Session,
    *,
    account_id: UUID | str,
    statut: str | None = None,
    type_impact: str | None = None,
    page: int = 1,
    limit: int = 25,
) -> tuple[list[ProjetRow], int]:
    if page < 1:
        page = 1
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100
    where = ["account_id = CAST(:aid AS UUID)", "deleted_at IS NULL"]
    params: dict[str, Any] = {"aid": str(account_id)}
    if statut is not None:
        where.append("statut = :statut")
        params["statut"] = statut
    if type_impact is not None:
        where.append(":ti = ANY(types_impact)")
        params["ti"] = type_impact

    where_sql = " AND ".join(where)
    total = db.execute(
        text(f"SELECT COUNT(*) FROM projet WHERE {where_sql}"), params
    ).scalar_one()

    params["limit"] = limit
    params["offset"] = (page - 1) * limit
    rows = db.execute(
        text(
            f"SELECT {_SELECT_COLS} FROM projet WHERE {where_sql} "
            "ORDER BY updated_at DESC NULLS LAST, created_at DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).all()
    return [_row_to_dataclass(r) for r in rows], int(total)


def get_projet(
    db: Session, *, projet_id: UUID | str, account_id: UUID | str
) -> ProjetRow:
    r = _select_one(db, projet_id=projet_id, account_id=account_id)
    if r is None:
        raise ProjetNotFound()
    return r


def create_projet(
    db: Session,
    *,
    account_id: UUID | str,
    user_id: UUID | str,
    payload: dict[str, Any],
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> ProjetRow:
    nom = payload.get("nom")
    if not nom or not isinstance(nom, str):
        raise ValueError("nom obligatoire pour un projet")

    types_impact = validate_types_impact(payload.get("types_impact"))
    structure = validate_structure_financement(payload.get("structure_financement_arr"))
    indicateurs = validate_indicateurs(payload.get("indicateurs_impact_json"))
    statut = validate_statut(payload.get("statut") or "brouillon")
    maturite = validate_maturite(payload.get("maturite"))

    money = payload.get("montant_recherche")
    amount, currency = None, None
    if money is not None:
        amount = (money.get("amount") if isinstance(money, dict) else getattr(money, "amount", None))
        currency = (
            money.get("currency") if isinstance(money, dict) else getattr(money, "currency", None)
        )

    entreprise_id = _entreprise_id(db, account_id)

    new_id = uuid.uuid4()
    sql = text(
        """
        INSERT INTO projet (
            id, account_id, entreprise_id, nom, description,
            objectif_environnemental, types_impact, maturite,
            montant_recherche_amount, montant_recherche_currency,
            duree_mois, structure_financement_arr,
            indicateurs_impact_json,
            localisation_pays_iso2, localisation_ville,
            statut, version, created_by, created_at, updated_at
        )
        VALUES (
            CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:eid AS UUID),
            :nom, :description,
            :obj_env, :types_impact, :maturite,
            :amount, :currency,
            :duree, :structure,
            CAST(:indicateurs AS JSONB),
            :pays, :ville,
            :statut, 1, CAST(:uid AS UUID), now(), now()
        )
        """
    )
    db.execute(
        sql,
        {
            "id": str(new_id),
            "aid": str(account_id),
            "eid": str(entreprise_id),
            "nom": nom,
            "description": payload.get("description"),
            "obj_env": payload.get("objectif_environnemental"),
            "types_impact": types_impact,
            "maturite": maturite,
            "amount": amount,
            "currency": currency,
            "duree": payload.get("duree_mois"),
            "structure": structure,
            "indicateurs": _json.dumps(indicateurs) if indicateurs else None,
            "pays": payload.get("localisation_pays_iso2"),
            "ville": payload.get("localisation_ville"),
            "statut": statut,
            "uid": str(user_id) if user_id else None,
        },
    )
    db.flush()

    record_audit(
        db,
        entity_type="projet",
        entity_id=new_id,
        field=None,
        old=None,
        new={"nom": nom, "statut": statut},
        source_of_change=source_of_change,
        user_id=user_id,
        account_id=account_id,
        notes="projet.created",
    )

    row = _select_one(db, projet_id=new_id, account_id=account_id)
    if row is None:
        raise RuntimeError("projet vanished after insert")

    publish_sync(
        account_id,
        {
            "type": "projet.created",
            "projet_id": str(row.id),
            "version": row.version,
            "source_of_change": str(source_of_change.value),
        },
    )
    return row


def _diff(current: ProjetRow, payload: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
    cur_map: dict[str, Any] = {
        "nom": current.nom,
        "description": current.description,
        "objectif_environnemental": current.objectif_environnemental,
        "types_impact": current.types_impact,
        "maturite": current.maturite,
        "montant_recherche": (
            {"amount": current.montant_recherche_amount,
             "currency": current.montant_recherche_currency}
            if (current.montant_recherche_amount is not None
                or current.montant_recherche_currency is not None)
            else None
        ),
        "duree_mois": current.duree_mois,
        "structure_financement_arr": current.structure_financement_arr,
        "indicateurs_impact_json": current.indicateurs_impact_json,
        "localisation_pays_iso2": current.localisation_pays_iso2,
        "localisation_ville": current.localisation_ville,
        "statut": current.statut,
    }
    diff: dict[str, tuple[Any, Any]] = {}
    for logical, new_val in payload.items():
        if logical not in cur_map:
            continue
        old_val = cur_map[logical]
        if logical == "montant_recherche":
            old_norm = (
                {"amount": str(old_val["amount"]) if old_val.get("amount") is not None else None,
                 "currency": old_val.get("currency")}
                if isinstance(old_val, dict) else None
            )
            if new_val is None:
                new_norm = None
            elif isinstance(new_val, dict):
                amt = new_val.get("amount")
                new_norm = {
                    "amount": str(amt) if amt is not None else None,
                    "currency": new_val.get("currency"),
                }
            else:
                amt = getattr(new_val, "amount", None)
                new_norm = {
                    "amount": str(amt) if amt is not None else None,
                    "currency": getattr(new_val, "currency", None),
                }
            if old_norm != new_norm:
                diff[logical] = (old_val, new_val)
        else:
            if old_val != new_val:
                diff[logical] = (old_val, new_val)
    return diff


def patch_projet(
    db: Session,
    *,
    projet_id: UUID | str,
    account_id: UUID | str,
    user_id: UUID | str,
    expected_version: int,
    payload: dict[str, Any],
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> ProjetRow:
    current = get_projet(db, projet_id=projet_id, account_id=account_id)
    if current.version != expected_version:
        raise VersionConflict(current.version, expected_version)

    # Validation explicite des champs modifiables.
    if "types_impact" in payload:
        payload["types_impact"] = validate_types_impact(payload["types_impact"])
    if "structure_financement_arr" in payload:
        payload["structure_financement_arr"] = validate_structure_financement(
            payload["structure_financement_arr"]
        )
    if "indicateurs_impact_json" in payload:
        payload["indicateurs_impact_json"] = validate_indicateurs(
            payload["indicateurs_impact_json"]
        )
    if "statut" in payload:
        payload["statut"] = validate_statut(payload["statut"])
    if "maturite" in payload:
        payload["maturite"] = validate_maturite(payload["maturite"])

    diff = _diff(current, payload)
    if not diff:
        return current

    sets: list[str] = ["version = version + 1", "updated_at = now()"]
    params: dict[str, Any] = {
        "id": str(current.id),
        "expected_version": expected_version,
    }

    column_map = {
        "nom": ("nom", "scalar"),
        "description": ("description", "scalar"),
        "objectif_environnemental": ("objectif_environnemental", "scalar"),
        "types_impact": ("types_impact", "array"),
        "maturite": ("maturite", "scalar"),
        "duree_mois": ("duree_mois", "scalar"),
        "structure_financement_arr": ("structure_financement_arr", "array"),
        "indicateurs_impact_json": ("indicateurs_impact_json", "jsonb"),
        "localisation_pays_iso2": ("localisation_pays_iso2", "scalar"),
        "localisation_ville": ("localisation_ville", "scalar"),
        "statut": ("statut", "scalar"),
    }

    for logical, new_val in payload.items():
        if logical == "montant_recherche":
            if new_val is None:
                sets.append("montant_recherche_amount = NULL, montant_recherche_currency = NULL")
            else:
                amt = new_val.get("amount") if isinstance(new_val, dict) else getattr(new_val, "amount", None)
                cur = new_val.get("currency") if isinstance(new_val, dict) else getattr(new_val, "currency", None)
                sets.append("montant_recherche_amount = :v_amount")
                sets.append("montant_recherche_currency = :v_currency")
                params["v_amount"] = amt
                params["v_currency"] = cur
            continue
        if logical not in column_map:
            continue
        col, kind = column_map[logical]
        bind = f"v_{col}"
        if kind == "jsonb":
            sets.append(f"{col} = CAST(:{bind} AS JSONB)")
            params[bind] = _json.dumps(new_val) if new_val is not None else None
        else:
            sets.append(f"{col} = :{bind}")
            params[bind] = new_val

    sql = text(
        f"""
        UPDATE projet SET {", ".join(sets)}
        WHERE id = CAST(:id AS UUID)
          AND version = :expected_version
        RETURNING version
        """
    )
    res = db.execute(sql, params).first()
    if res is None:
        cur = db.execute(
            text("SELECT version FROM projet WHERE id = CAST(:id AS UUID)"),
            {"id": str(current.id)},
        ).scalar_one_or_none()
        if cur is None:
            raise ProjetNotFound()
        raise VersionConflict(int(cur), expected_version)

    for field, (old_v, new_v) in diff.items():
        record_audit(
            db,
            entity_type="projet",
            entity_id=current.id,
            field=field,
            old=_jsonable(old_v),
            new=_jsonable(new_v),
            source_of_change=source_of_change,
            user_id=user_id,
            account_id=account_id,
        )

    refreshed = _select_one(db, projet_id=current.id, account_id=account_id)
    if refreshed is None:
        raise RuntimeError("projet vanished after update")
    publish_sync(
        account_id,
        {
            "type": "projet.updated",
            "projet_id": str(refreshed.id),
            "version": refreshed.version,
            "fields_changed": list(diff.keys()),
            "source_of_change": str(source_of_change.value),
        },
    )
    return refreshed


def duplicate_projet(
    db: Session,
    *,
    projet_id: UUID | str,
    account_id: UUID | str,
    user_id: UUID | str,
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> ProjetRow:
    current = get_projet(db, projet_id=projet_id, account_id=account_id)
    new_payload = {
        "nom": f"{current.nom} (copie)",
        "description": current.description,
        "objectif_environnemental": current.objectif_environnemental,
        "types_impact": current.types_impact,
        "maturite": current.maturite,
        "montant_recherche": (
            {"amount": current.montant_recherche_amount,
             "currency": current.montant_recherche_currency}
            if current.montant_recherche_amount is not None else None
        ),
        "duree_mois": current.duree_mois,
        "structure_financement_arr": current.structure_financement_arr,
        "indicateurs_impact_json": current.indicateurs_impact_json,
        "localisation_pays_iso2": current.localisation_pays_iso2,
        "localisation_ville": current.localisation_ville,
        "statut": "brouillon",
    }
    new_row = create_projet(
        db,
        account_id=account_id,
        user_id=user_id,
        payload=new_payload,
        source_of_change=source_of_change,
    )
    record_audit(
        db,
        entity_type="projet",
        entity_id=new_row.id,
        field="duplicated_from",
        old=None,
        new=str(current.id),
        source_of_change=source_of_change,
        user_id=user_id,
        account_id=account_id,
        notes="projet.duplicated",
    )
    return new_row


def delete_projet(
    db: Session,
    *,
    projet_id: UUID | str,
    account_id: UUID | str,
    user_id: UUID | str,
    confirm: bool = False,
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> None:
    current = get_projet(db, projet_id=projet_id, account_id=account_id)
    protected = current.statut in ("finance", "en_execution")
    if protected and not confirm:
        raise DeleteProtected(current.statut or "")

    db.execute(
        text("UPDATE projet SET deleted_at = now(), updated_at = now() "
             "WHERE id = CAST(:id AS UUID) AND account_id = CAST(:aid AS UUID)"),
        {"id": str(current.id), "aid": str(account_id)},
    )
    record_audit(
        db,
        entity_type="projet",
        entity_id=current.id,
        field="deleted_at",
        old=None,
        new="now",
        source_of_change=source_of_change,
        user_id=user_id,
        account_id=account_id,
        notes="projet.deleted",
    )
    publish_sync(
        account_id,
        {"type": "projet.deleted", "projet_id": str(current.id)},
    )


def transition_projet(
    db: Session,
    *,
    projet_id: UUID | str,
    account_id: UUID | str,
    user_id: UUID | str,
    expected_version: int,
    to: str,
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> ProjetRow:
    new_statut = validate_statut(to)
    return patch_projet(
        db,
        projet_id=projet_id,
        account_id=account_id,
        user_id=user_id,
        expected_version=expected_version,
        payload={"statut": new_statut},
        source_of_change=source_of_change,
    )


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    return v


def aggregate_read(row: ProjetRow) -> dict[str, Any]:
    montant = None
    if row.montant_recherche_amount is not None and row.montant_recherche_currency is not None:
        montant = {
            "amount": row.montant_recherche_amount,
            "currency": row.montant_recherche_currency,
        }
    return {
        "id": row.id,
        "account_id": row.account_id,
        "entreprise_id": row.entreprise_id,
        "version": row.version,
        "nom": row.nom,
        "description": row.description,
        "objectif_environnemental": row.objectif_environnemental,
        "types_impact": row.types_impact,
        "maturite": row.maturite,
        "montant_recherche": montant,
        "duree_mois": row.duree_mois,
        "structure_financement_arr": row.structure_financement_arr,
        "indicateurs_impact_json": row.indicateurs_impact_json,
        "localisation_pays_iso2": row.localisation_pays_iso2,
        "localisation_ville": row.localisation_ville,
        "statut": row.statut,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def aggregate_summary(row: ProjetRow) -> dict[str, Any]:
    montant = None
    if row.montant_recherche_amount is not None and row.montant_recherche_currency is not None:
        montant = {
            "amount": row.montant_recherche_amount,
            "currency": row.montant_recherche_currency,
        }
    return {
        "id": row.id,
        "nom": row.nom,
        "statut": row.statut,
        "types_impact": row.types_impact,
        "maturite": row.maturite,
        "montant_recherche": montant,
        "updated_at": row.updated_at,
    }
