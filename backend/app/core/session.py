"""F02 — Helpers SET LOCAL pour le contexte RLS Postgres.

Toujours utilisé dans une transaction. Les settings sont purgés en fin de tx.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session


def set_db_session_context(
    conn: Connection | Session,
    *,
    user_id: UUID | str | None,
    account_id: UUID | str | None,
    is_admin: bool,
) -> None:
    """Pose les ``SET LOCAL`` Postgres pour la transaction courante.

    - ``app.current_user_id`` : UUID utilisateur (toujours, sauf anonyme).
    - ``app.current_account_id`` : UUID account (PME uniquement).
    - ``app.is_admin`` : ``'true'`` si admin, sinon ``'false'``.
    """
    runner: Any = conn

    def _exec(sql: str, params: dict | None = None) -> None:
        runner.execute(text(sql), params or {})

    # SET LOCAL n'accepte pas de paramètre lié, on inline les valeurs sécurisées.
    if user_id is not None:
        _exec(f"SET LOCAL app.current_user_id = '{UUID(str(user_id))}'")
    else:
        _exec("SET LOCAL app.current_user_id = ''")

    if account_id is not None:
        _exec(f"SET LOCAL app.current_account_id = '{UUID(str(account_id))}'")
    else:
        _exec("SET LOCAL app.current_account_id = ''")

    _exec(f"SET LOCAL app.is_admin = '{'true' if is_admin else 'false'}'")
