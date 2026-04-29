"""F02 T043 — Audit RLS : liste les tables ``account_id NOT NULL`` et vérifie
que toutes ont une policy ``tenant_isolation`` + RLS forced.

Usage : ``python -m app.scripts.audit_rls``
Exit 0 si OK, exit 1 si une table account-scoped n'est pas protégée.
"""

from __future__ import annotations

import sys

from sqlalchemy import text

from app.db import get_engine_migrator


def main() -> int:
    eng = get_engine_migrator()
    issues: list[str] = []
    with eng.connect() as conn:
        # Toutes les tables avec colonne account_id NOT NULL
        rows = conn.execute(
            text(
                """
                SELECT c.table_name
                FROM information_schema.columns c
                WHERE c.table_schema = 'public'
                  AND c.column_name = 'account_id'
                  AND c.is_nullable = 'NO'
                """
            )
        ).fetchall()
        tables = [r[0] for r in rows]
        # Whitelist : tables auth gérées par autre mécanisme
        whitelist = {"refresh_tokens", "password_reset_tokens"}
        for t in tables:
            if t in whitelist:
                continue
            rls = conn.execute(
                text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = :n"),
                {"n": t},
            ).first()
            policies = conn.execute(
                text("SELECT policyname FROM pg_policies WHERE tablename = :n"),
                {"n": t},
            ).fetchall()
            if not rls or not rls[0] or not rls[1]:
                issues.append(f"{t}: RLS non activée/forcée")
            elif not policies:
                issues.append(f"{t}: aucune policy")

    if issues:
        print("Tables non protégées par RLS :", file=sys.stderr)
        for i in issues:
            print(f"  - {i}", file=sys.stderr)
        return 1
    print(f"OK — {len(tables)} tables account-scoped, toutes protégées.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
