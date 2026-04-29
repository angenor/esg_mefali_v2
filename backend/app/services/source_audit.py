"""F03 — Hook d'audit pour transitions de statut Source.

L'insertion principale dans ``audit_log`` est faite par le trigger SQL
``source_status_version_trg`` (cf. migration 0003). Ce module expose un helper
Python pour l'audit "applicatif" facultatif (transitions issues du service —
F04 consommera ce point d'extension).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def record_source_transition(
    db: Session,
    *,
    source_id: uuid.UUID,
    old_status: str | None,
    new_status: str,
    actor_user_id: uuid.UUID | None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Insère une trace dans ``audit_log`` pour une transition de Source.

    Idempotence : aucun garde — l'appelant doit éviter le double-call.
    """
    db.execute(
        text(
            """
            INSERT INTO audit_log
              (id, user_id, account_id, entity_type, entity_id,
               field, old_value, new_value, source_of_change)
            VALUES
              (gen_random_uuid(), :uid, NULL, 'source', :sid,
               'verification_status', to_jsonb(:old::text), to_jsonb(:new::text),
               'admin')
            """
        ),
        {
            "uid": str(actor_user_id) if actor_user_id else None,
            "sid": str(source_id),
            "old": old_status,
            "new": new_status,
        },
    )
    if extra:
        # Place-holder : F04 affinera (champs structurés)
        pass
