"""F03 US2 — Tool ``flag_unsourced``.

Use when : aucune source ``verified`` ne couvre une affirmation que l'utilisateur
réclame ; tu choisis de répondre "Je ne dispose pas de source vérifiée".

Don't use when : tu n'as simplement pas cherché.

L'``account_id`` est lu via ``current_setting('app.current_account_id')`` (RLS F02).
``user_id`` peut être ``NULL`` pour un appel système (FR-007 clarifié).
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.source import FlagUnsourcedInput, FlagUnsourcedOutput


def handle_flag_unsourced(
    db: Session,
    payload: FlagUnsourcedInput,
    *,
    user_id: uuid.UUID | None = None,
) -> FlagUnsourcedOutput:
    """Insère un claim non sourcé. account_id est résolu via RLS context."""
    new_id = uuid.uuid4()
    db.execute(
        text(
            """
            INSERT INTO unsourced_claim_log
              (id, account_id, user_id, claim_text, context_json)
            VALUES
              (:id,
               NULLIF(current_setting('app.current_account_id', true), '')::uuid,
               :uid, :claim, :ctx::jsonb)
            """
        ),
        {
            "id": str(new_id),
            "uid": str(user_id) if user_id else None,
            "claim": payload.claim,
            "ctx": __import__("json").dumps(payload.context),
        },
    )
    return FlagUnsourcedOutput(id=new_id)
