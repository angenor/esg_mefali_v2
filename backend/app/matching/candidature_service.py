"""F25 — Création de candidature à partir d'un match (US7).

Construit un snapshot canonicalisé (SHA-256), insère la candidature en
``statut='brouillon'``, journalise via ``record_audit`` (F04).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.matching import service as matching_service


class ProjetNotFound(Exception):
    pass


class OffreNotFound(Exception):
    pass


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _build_snapshot(
    db: Session, *, account_id: UUID, projet_id: UUID, offre_id: UUID
) -> dict[str, Any]:
    projet = matching_service._load_projet(
        db, account_id=account_id, projet_id=projet_id
    )
    if projet is None:
        raise ProjetNotFound(str(projet_id))
    offres = [
        o
        for o in matching_service._load_offres_published(db)
        if str(o.get("offre_id")) == str(offre_id)
    ]
    if not offres:
        raise OffreNotFound(str(offre_id))
    detail = matching_service.detail(
        db, account_id=account_id, projet_id=projet_id, offre_id=offre_id
    )
    serialized = matching_service.serialize_match_detail(detail)
    offre_row = offres[0]
    return {
        "schema_version": 1,
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "projet": {
            "id": str(projet["id"]),
            "account_id": str(projet["account_id"]),
            "montant_recherche": {
                "amount": str(projet.get("montant_recherche_amount") or "0"),
                "currency": projet.get("montant_recherche_currency"),
            },
            "types_impact": projet.get("types_impact") or [],
            "localisation_pays_iso2": projet.get("localisation_pays_iso2"),
            "structure_financement_arr": projet.get("structure_financement_arr") or [],
        },
        "offre": {
            "id": str(offre_row["offre_id"]),
            "name": offre_row.get("offre_name"),
            "fonds_id": str(offre_row["fonds_id"]),
            "intermediaire_id": (
                str(offre_row["intermediaire_id"])
                if offre_row.get("intermediaire_id")
                else None
            ),
            "fonds_name": offre_row.get("fonds_name"),
            "intermediaire_name": offre_row.get("intermediaire_name"),
            "source_ids_fonds": [
                str(s) for s in (offre_row.get("fonds_source_ids") or [])
            ],
            "source_ids_intermediaire": [
                str(s) for s in (offre_row.get("intermediaire_source_ids") or [])
            ],
        },
        "scoring": serialized,
    }


def _hash(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()


def create_candidature(
    db: Session,
    *,
    account_id: UUID,
    projet_id: UUID,
    offre_id: UUID,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    snapshot = _build_snapshot(
        db, account_id=account_id, projet_id=projet_id, offre_id=offre_id
    )
    snapshot_hash = _hash(snapshot)
    candidature_id = uuid.uuid4()

    db.execute(
        text(
            """
            INSERT INTO candidature
              (id, account_id, projet_id, offre_id, statut, snapshot_json, version, created_by)
            VALUES
              (CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:pid AS UUID),
               CAST(:oid AS UUID), :statut, CAST(:snap AS JSONB), 1, CAST(:uid AS UUID))
            """
        ),
        {
            "id": str(candidature_id),
            "aid": str(account_id),
            "pid": str(projet_id),
            "oid": str(offre_id),
            "statut": "brouillon",
            "snap": json.dumps(
                {**snapshot, "snapshot_hash": snapshot_hash}, default=str
            ),
            "uid": str(user_id) if user_id else None,
        },
    )

    record_audit(
        db,
        entity_type="candidature",
        entity_id=candidature_id,
        field="create",
        old=None,
        new={
            "projet_id": str(projet_id),
            "offre_id": str(offre_id),
            "statut": "brouillon",
            "snapshot_hash": snapshot_hash,
        },
        source_of_change=SourceOfChange.MANUAL,
        user_id=str(user_id) if user_id else None,
        account_id=str(account_id),
    )

    return {
        "candidature_id": str(candidature_id),
        "snapshot_hash": snapshot_hash,
        "statut": "brouillon",
    }
