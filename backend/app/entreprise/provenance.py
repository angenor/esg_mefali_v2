"""F11 — Calcul de la provenance par champ via audit_log (F04)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

TRACKED_FIELDS: tuple[str, ...] = (
    "name",
    "secteur_code",
    "secteur_label",
    "taille_ca",
    "taille_effectifs",
    "localisation_siege_pays_iso2",
    "localisation_siege_ville",
    "zones_operation_pays_iso2",
    "gouvernance_json",
    "pratiques_actuelles_json",
)


def aggregate_field_meta(
    db: Session, *, entreprise_id: UUID | str
) -> dict[str, dict[str, Any]]:
    """Retourne {field: {source_of_change, last_modified_at, last_modified_by}}.

    Récupère, pour chaque champ tracké, la dernière mutation enregistrée dans
    audit_log pour entity_type='entreprise' & entity_id=<id>.
    """
    sql = text(
        """
        SELECT DISTINCT ON (field)
            field, source_of_change, "timestamp", user_id
        FROM audit_log
        WHERE entity_type = 'entreprise'
          AND entity_id = CAST(:eid AS UUID)
          AND field IS NOT NULL
        ORDER BY field, "timestamp" DESC
        """
    )
    rows = db.execute(sql, {"eid": str(entreprise_id)}).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        field = r[0]
        src = r[1]
        ts = r[2]
        uid = r[3]
        out[field] = {
            "source_of_change": str(src) if src is not None else None,
            "last_modified_at": ts if isinstance(ts, datetime) else None,
            "last_modified_by": uid,
        }
    return out
