"""F02 T067 — Audit des routes FastAPI : confirme la présence d'une dépendance
``get_current_user`` (ou get_current_admin/pme) sur toutes les routes hors
whitelist.

Usage : ``python -m app.scripts.audit_routes``
Sortie : exit 0 si OK, exit 1 si une route protégeable est exposée sans auth.
"""

from __future__ import annotations

import sys

from fastapi.routing import APIRoute

WHITELIST_PATHS = {
    "/health",
    "/auth/register",
    "/auth/login",
    "/auth/logout",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}

ALLOWED_DEPS = {"get_current_user", "get_current_admin", "get_current_pme"}


def main() -> int:
    from app.main import app

    issues: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path
        if path in WHITELIST_PATHS:
            continue
        deps = {d.call.__name__ for d in route.dependant.dependencies if d.call}
        if not (deps & ALLOWED_DEPS):
            issues.append(f"  - {route.methods} {path}")
    if issues:
        print("Routes sans dépendance d'auth :", file=sys.stderr)
        for i in issues:
            print(i, file=sys.stderr)
        return 1
    print(f"OK — {len(list(app.routes))} routes auditées, aucune fuite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
