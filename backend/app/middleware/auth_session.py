"""F02 — Middleware ASGI de session : valide le CSRF et décode le JWT cookie
pour exposer ``request.state.user_payload``.

Le chargement effectif de l'utilisateur + l'application du contexte RLS sont
faits par la dépendance FastAPI ``get_current_user`` afin de garder le
middleware simple et déterministe.

T013 — référence plan.md.
"""

from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.security import InvalidTokenError, decode_access_token, verify_csrf_token

logger = logging.getLogger(__name__)

ACCESS_COOKIE = "mefali_at"
REFRESH_COOKIE = "mefali_rt"  # noqa: S105
CSRF_COOKIE = "mefali_csrf"  # noqa: S105
CSRF_HEADER = "x-csrf-token"

# Endpoints exemptés de CSRF : pas encore de cookie CSRF côté client.
CSRF_EXEMPT_PATHS = frozenset(
    {
        "/auth/register",
        "/auth/login",
        "/auth/forgot-password",
        "/auth/reset-password",
    }
)
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class AuthSessionMiddleware(BaseHTTPMiddleware):
    """Middleware léger : CSRF + décodage JWT (sans I/O DB)."""

    async def dispatch(self, request: Request, call_next):
        # 1) CSRF check sur méthodes mutantes
        if (
            request.method.upper() not in SAFE_METHODS
            and request.url.path not in CSRF_EXEMPT_PATHS
        ):
            cookie_csrf = request.cookies.get(CSRF_COOKIE, "")
            header_csrf = request.headers.get(CSRF_HEADER, "")
            if not verify_csrf_token(header_csrf, cookie_csrf):
                return JSONResponse(
                    status_code=403,
                    content={"error": {"code": "csrf_invalid", "message": "CSRF token invalide."}},
                )

        # 2) Décode JWT (best-effort, jamais d'exception)
        request.state.user_payload = None
        access = request.cookies.get(ACCESS_COOKIE)
        if access:
            try:
                request.state.user_payload = decode_access_token(access)
            except InvalidTokenError:
                request.state.user_payload = None

        return await call_next(request)
