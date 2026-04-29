"""F07 — Permissions métier sur les sources.

- ``assert_admin`` est déjà fourni par ``app.auth.dependencies.get_current_admin``.
- ``assert_can_verify`` impose le contrôle 4 yeux : un admin ne peut pas
  valider sa propre source (cf. spec FR Q1 + US2).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping

from fastapi import HTTPException, status

ERROR_SELF_VERIFICATION = "self_verification_forbidden"


def assert_can_verify(
    source: Mapping[str, object], actor_id: uuid.UUID | str
) -> None:
    """Lève ``HTTPException(409)`` si l'``actor_id`` est le créateur."""
    captured_by = source.get("captured_by")
    if captured_by is None:
        return
    if str(captured_by) == str(actor_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": ERROR_SELF_VERIFICATION,
                "message": (
                    "Vous ne pouvez pas valider une source que vous avez "
                    "créée — un autre administrateur doit la vérifier."
                ),
            },
        )


__all__ = ["assert_can_verify", "ERROR_SELF_VERIFICATION"]
