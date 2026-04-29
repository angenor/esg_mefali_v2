"""Application FastAPI — point d'entrée.

Endpoints F01 :
- GET /health → 200 si DB OK ; 503 sinon.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db as db_module

logger = logging.getLogger(__name__)

app = FastAPI(title="ESG Mefali API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Any:
    """Sonde de santé.

    Exécute ``SELECT 1`` avec un statement_timeout de 2 s.
    Retourne 200 si OK, 503 sinon (jamais d'exception qui fuite).
    """
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
        except Exception:  # noqa: BLE001 — best-effort cleanup
            pass
