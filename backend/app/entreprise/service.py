"""F11 — Service métier du profil entreprise.

Responsabilités :
- get_or_provision_entreprise(account_id) : lit ou crée la row 1:1.
- update_partial(...) : applique mutations + audit + version++.
- aggregate_read(...) : assemble dict prêt pour EntrepriseRead avec field_meta.
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
from app.entreprise.events import publish_sync
from app.entreprise.provenance import aggregate_field_meta
from app.entreprise.taxonomy import get_sector


class VersionConflict(Exception):
    """Raised when If-Match version is stale."""

    def __init__(self, current_version: int, your_version: int) -> None:
        self.current_version = current_version
        self.your_version = your_version
        super().__init__(
            f"version conflict (current={current_version}, your={your_version})"
        )


@dataclass(frozen=True)
class EntrepriseRow:
    id: UUID
    account_id: UUID
    version: int
    name: str | None
    secteur_code: str | None
    secteur_label: str | None
    taille_ca_amount: Decimal | None
    taille_ca_currency: str | None
    taille_effectifs: int | None
    localisation_siege_pays_iso2: str | None
    localisation_siege_ville: str | None
    zones_operation_pays_iso2: list[str] | None
    gouvernance_json: dict[str, Any] | None
    pratiques_actuelles_json: dict[str, Any] | None
    created_at: datetime | None
    updated_at: datetime | None


def _row_to_dataclass(r: Any) -> EntrepriseRow:
    return EntrepriseRow(
        id=r.id,
        account_id=r.account_id,
        version=r.version,
        name=r.name,
        secteur_code=r.secteur_code,
        secteur_label=r.secteur_label,
        taille_ca_amount=r.taille_ca_amount,
        taille_ca_currency=r.taille_ca_currency,
        taille_effectifs=r.taille_effectifs,
        localisation_siege_pays_iso2=(
            r.localisation_siege_pays_iso2.strip()
            if r.localisation_siege_pays_iso2 else None
        ),
        localisation_siege_ville=r.localisation_siege_ville,
        zones_operation_pays_iso2=(
            list(r.zones_operation_pays_iso2)
            if r.zones_operation_pays_iso2 is not None
            else None
        ),
        gouvernance_json=r.gouvernance_json,
        pratiques_actuelles_json=r.pratiques_actuelles_json,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _select_one(db: Session, *, account_id: UUID | str) -> EntrepriseRow | None:
    sql = text(
        """
        SELECT id, account_id, version, name,
               secteur_code, secteur_label,
               taille_ca_amount, taille_ca_currency, taille_effectifs,
               localisation_siege_pays_iso2, localisation_siege_ville,
               zones_operation_pays_iso2,
               gouvernance_json, pratiques_actuelles_json,
               created_at, updated_at
        FROM entreprise
        WHERE account_id = CAST(:aid AS UUID)
          AND deleted_at IS NULL
        LIMIT 1
        """
    )
    row = db.execute(sql, {"aid": str(account_id)}).first()
    if row is None:
        return None
    return _row_to_dataclass(row)


def get_or_provision_entreprise(
    db: Session, *, account_id: UUID | str, user_id: UUID | str | None = None
) -> EntrepriseRow:
    """Lit la row entreprise 1:1 ; provisionne automatiquement si absente."""
    existing = _select_one(db, account_id=account_id)
    if existing is not None:
        return existing

    new_id = uuid.uuid4()
    db.execute(
        text(
            """
            INSERT INTO entreprise (id, account_id, name, version,
                                    created_by, created_at, updated_at)
            VALUES (CAST(:id AS UUID), CAST(:aid AS UUID), '', 1,
                    CAST(:uid AS UUID), now(), now())
            ON CONFLICT (account_id) DO NOTHING
            """
        ),
        {
            "id": str(new_id),
            "aid": str(account_id),
            "uid": str(user_id) if user_id else None,
        },
    )
    db.flush()
    refreshed = _select_one(db, account_id=account_id)
    if refreshed is None:
        raise RuntimeError("entreprise provisioning failed unexpectedly")
    return refreshed


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Si `taille_ca` arrive en bloc, l'éclate en (amount, currency)."""
    out: dict[str, Any] = {}
    for k, v in payload.items():
        if k == "taille_ca" and v is not None:
            if isinstance(v, dict):
                out["taille_ca_amount"] = v.get("amount")
                out["taille_ca_currency"] = v.get("currency")
            else:
                out["taille_ca_amount"] = getattr(v, "amount", None)
                out["taille_ca_currency"] = getattr(v, "currency", None)
        elif k == "taille_ca" and v is None:
            out["taille_ca_amount"] = None
            out["taille_ca_currency"] = None
        else:
            out[k] = v
    return out


def _diff_old_new(
    current: EntrepriseRow, new_payload: dict[str, Any]
) -> dict[str, tuple[Any, Any]]:
    """Retourne {logical_field: (old, new)} pour les champs effectivement changés."""
    diff: dict[str, tuple[Any, Any]] = {}
    cur_map: dict[str, Any] = {
        "name": current.name,
        "secteur_code": current.secteur_code,
        "secteur_label": current.secteur_label,
        "taille_ca": (
            {
                "amount": current.taille_ca_amount,
                "currency": current.taille_ca_currency,
            }
            if (
                current.taille_ca_amount is not None
                or current.taille_ca_currency is not None
            )
            else None
        ),
        "taille_effectifs": current.taille_effectifs,
        "localisation_siege_pays_iso2": current.localisation_siege_pays_iso2,
        "localisation_siege_ville": current.localisation_siege_ville,
        "zones_operation_pays_iso2": current.zones_operation_pays_iso2,
        "gouvernance_json": current.gouvernance_json,
        "pratiques_actuelles_json": current.pratiques_actuelles_json,
    }
    for logical, new_val in new_payload.items():
        if logical not in cur_map:
            continue
        old_val = cur_map[logical]
        if logical == "taille_ca":
            old_norm = (
                {
                    "amount": str(old_val["amount"])
                    if old_val.get("amount") is not None
                    else None,
                    "currency": old_val.get("currency"),
                }
                if isinstance(old_val, dict)
                else None
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


def _apply_update(
    db: Session,
    *,
    entreprise_id: UUID,
    expected_version: int,
    payload: dict[str, Any],
) -> int:
    norm = _normalize_payload(payload)

    if "secteur_code" in norm and norm.get("secteur_code") is not None:
        s = get_sector(norm["secteur_code"])
        if s is not None and "secteur_label" not in norm:
            norm["secteur_label"] = s.label

    sets: list[str] = ["version = version + 1", "updated_at = now()"]
    params: dict[str, Any] = {
        "id": str(entreprise_id),
        "expected_version": expected_version,
    }

    column_keys = {
        "name", "secteur_code", "secteur_label",
        "taille_ca_amount", "taille_ca_currency", "taille_effectifs",
        "localisation_siege_pays_iso2", "localisation_siege_ville",
        "zones_operation_pays_iso2", "gouvernance_json", "pratiques_actuelles_json",
    }
    for k, v in norm.items():
        if k not in column_keys:
            continue
        bind = f"v_{k}"
        if k in ("gouvernance_json", "pratiques_actuelles_json"):
            sets.append(f"{k} = CAST(:{bind} AS JSONB)")
            params[bind] = _json.dumps(v) if v is not None else None
        elif k == "zones_operation_pays_iso2":
            sets.append(f"{k} = :{bind}")
            params[bind] = v
        else:
            sets.append(f"{k} = :{bind}")
            params[bind] = v

    sql = text(
        f"""
        UPDATE entreprise
        SET {", ".join(sets)}
        WHERE id = CAST(:id AS UUID)
          AND version = :expected_version
        RETURNING version
        """
    )
    res = db.execute(sql, params).first()
    if res is None:
        cur = db.execute(
            text("SELECT version FROM entreprise WHERE id = CAST(:id AS UUID)"),
            {"id": str(entreprise_id)},
        ).scalar_one_or_none()
        if cur is None:
            raise RuntimeError("entreprise row not found")
        raise VersionConflict(current_version=int(cur), your_version=expected_version)
    return int(res[0])


def update_partial(
    db: Session,
    *,
    account_id: UUID | str,
    user_id: UUID | str,
    expected_version: int,
    payload: dict[str, Any],
    source_of_change: SourceOfChange = SourceOfChange.MANUAL,
) -> EntrepriseRow:
    """Applique un PATCH partiel + audit log par champ + version++."""
    current = get_or_provision_entreprise(db, account_id=account_id, user_id=user_id)
    if current.version != expected_version:
        raise VersionConflict(
            current_version=current.version, your_version=expected_version
        )

    diff = _diff_old_new(current, payload)
    if not diff:
        return current

    _apply_update(
        db,
        entreprise_id=current.id,
        expected_version=expected_version,
        payload=payload,
    )

    for field, (old_v, new_v) in diff.items():
        record_audit(
            db,
            entity_type="entreprise",
            entity_id=current.id,
            field=field,
            old=_jsonable(old_v),
            new=_jsonable(new_v),
            source_of_change=source_of_change,
            user_id=user_id,
            account_id=account_id,
        )

    refreshed = _select_one(db, account_id=account_id)
    if refreshed is None:
        raise RuntimeError("entreprise vanished after update")

    publish_sync(
        account_id,
        {
            "type": "entreprise.updated",
            "entreprise_id": str(refreshed.id),
            "version": refreshed.version,
            "fields_changed": list(diff.keys()),
            "source_of_change": str(source_of_change.value),
        },
    )
    return refreshed


def _jsonable(v: Any) -> Any:
    """Convertit Decimal / dataclass-like en types JSON-able."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    return v


def aggregate_read(db: Session, row: EntrepriseRow) -> dict[str, Any]:
    """Construit un dict prêt pour EntrepriseRead (avec field_meta)."""
    field_meta = aggregate_field_meta(db, entreprise_id=row.id)
    taille_ca = None
    if row.taille_ca_amount is not None and row.taille_ca_currency is not None:
        taille_ca = {
            "amount": row.taille_ca_amount,
            "currency": row.taille_ca_currency,
        }
    return {
        "id": row.id,
        "account_id": row.account_id,
        "version": row.version,
        "name": row.name or None,
        "secteur_code": row.secteur_code,
        "secteur_label": row.secteur_label,
        "taille_ca": taille_ca,
        "taille_effectifs": row.taille_effectifs,
        "localisation_siege_pays_iso2": row.localisation_siege_pays_iso2,
        "localisation_siege_ville": row.localisation_siege_ville,
        "zones_operation_pays_iso2": row.zones_operation_pays_iso2,
        "gouvernance_json": row.gouvernance_json,
        "pratiques_actuelles_json": row.pratiques_actuelles_json,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "field_meta": field_meta,
    }
