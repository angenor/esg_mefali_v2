"""F02 — Helper ``record_event`` pour la table ``audit_log`` (F01).

T017 — référence research.md D-009.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def record_event(
    db: Session,
    *,
    event_type: str,
    actor_user_id: UUID | str | None = None,
    actor_account_id: UUID | str | None = None,
    payload: dict[str, Any] | None = None,
    source_of_change: str = "manual",
    entity_type: str = "auth",
    entity_id: UUID | str | None = None,
) -> None:
    """Insère une entrée dans ``audit_log`` (schéma F01).

    Mappe ``event_type`` -> ``new_value.event_type`` et ``payload`` ->
    ``new_value.payload`` car la table F01 n'a pas de colonne ``event_type``
    explicite (elle suit un modèle entity-changelog).
    """
    new_value = {"event_type": event_type, "payload": payload or {}}
    eid = str(entity_id) if entity_id else (str(actor_user_id) if actor_user_id else "00000000-0000-0000-0000-000000000000")
    try:
        # Savepoint pour ne pas tuer la transaction parente si l'insert échoue
        sp = db.begin_nested()
        try:
            db.execute(
                text(
                    """
                    INSERT INTO audit_log
                        (id, user_id, account_id, entity_type, entity_id,
                         new_value, source_of_change, created_at, version, updated_at, "timestamp")
                    VALUES
                        (gen_random_uuid(), :uid, :aid, :etype, :eid,
                         CAST(:nv AS JSONB), :src, now(), 1, now(), now())
                    """
                ),
                {
                    "uid": str(actor_user_id) if actor_user_id else None,
                    "aid": str(actor_account_id) if actor_account_id else None,
                    "etype": entity_type,
                    "eid": eid,
                    "nv": json.dumps(new_value),
                    "src": source_of_change,
                },
            )
            sp.commit()
        except Exception:
            sp.rollback()
            raise
    except Exception as exc:  # noqa: BLE001 — audit ne doit jamais casser le métier
        logger.warning("audit: échec d'insertion event_type=%s: %s", event_type, exc)
