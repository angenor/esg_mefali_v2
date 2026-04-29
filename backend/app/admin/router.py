"""F02 — Router admin : /admin/_rls_check.

T049 — Pour chaque table avec colonne ``account_id``, exécute un SELECT count(*)
**sans** définir ``app.current_account_id`` (via une connexion app_user dédiée).
Avec RLS activée, on doit obtenir 0 lignes pour chaque table.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.auth.dependencies import get_current_admin
from app.db import engine_app
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin", tags=["admin"])

# Tables F01 + F02 portant `account_id`.
ACCOUNT_SCOPED_TABLES = (
    "account_user",
    "entreprise",
    "projet",
    "candidature",
    "chat_message",
)


@router.get("/_rls_check")
def rls_check(_: AccountUser = Depends(get_current_admin)) -> dict:
    """Diagnostic RLS — admin only.

    Ouvre une nouvelle connexion app_user, ne pose AUCUN SET LOCAL, et compte
    les lignes de chaque table. Avec FORCE RLS, on doit obtenir 0 partout.
    """
    details = []
    all_ok = True
    with engine_app.connect() as conn:
        for tbl in ACCOUNT_SCOPED_TABLES:
            try:
                rows = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar() or 0
            except Exception:  # noqa: BLE001
                rows = -1
            try:
                rls = conn.execute(
                    text(
                        "SELECT relrowsecurity, relforcerowsecurity "
                        "FROM pg_class WHERE relname = :n"
                    ),
                    {"n": tbl},
                ).first()
            except Exception:  # noqa: BLE001
                rls = (False, False)
            rls_enabled = bool(rls[0]) if rls else False
            rls_forced = bool(rls[1]) if rls else False
            ok_table = (rows == 0) and rls_enabled and rls_forced
            if not ok_table:
                all_ok = False
            details.append(
                {
                    "table": tbl,
                    "rows_without_context": int(rows),
                    "rls_enabled": rls_enabled,
                    "rls_forced": rls_forced,
                }
            )
    return {
        "tables_checked": list(ACCOUNT_SCOPED_TABLES),
        "all_rls_enforced": all_ok,
        "details": details,
    }
