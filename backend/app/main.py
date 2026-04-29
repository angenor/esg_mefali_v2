"""Application FastAPI — point d'entrée.

Endpoints :
- F01 : GET /health.
- F02 : POST /auth/{register,login,refresh,logout,forgot-password,reset-password},
        GET /me, GET /admin/_rls_check.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db as db_module
from app.admin.router import router as admin_router
from app.api.routes.admin_unsourced import router as admin_unsourced_router
from app.api.routes.llm_tools import router as llm_tools_router
from app.api.routes.sources import router as sources_router
from app.auth.router import router as auth_router
from app.core.rate_limit import limiter
from app.middleware.auth_session import AuthSessionMiddleware
from app.users.router import router as users_router

logger = logging.getLogger(__name__)

app = FastAPI(title="ESG Mefali API", version="0.2.0")

# Rate limiting (slowapi)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):  # noqa: ARG001
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "rate_limited",
                "message": "Trop de tentatives. Réessayez plus tard.",
            }
        },
    )


# Auth session middleware
app.add_middleware(AuthSessionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*", "X-CSRF-Token"],
)

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(sources_router)
app.include_router(llm_tools_router)
app.include_router(admin_unsourced_router)


@app.get("/health")
def health() -> Any:
    """Sonde de santé. Retourne 200 si OK, 503 sinon."""
    session = db_module.SessionLocal()
    try:
        session.execute(text("SET LOCAL statement_timeout = 2000"))
        session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except SQLAlchemyError as exc:
        logger.warning("health: DB unreachable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unreachable"},
        )
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass
