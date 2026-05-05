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
from app.admin.crud_router import router as admin_crud_router
from app.admin.publish import router as admin_publish_router
from app.admin.router import router as admin_router
from app.admin.search import router as admin_search_router
from app.admin.stats import router as admin_stats_router
from app.api.routes.admin_llm_eval import router as admin_llm_eval_router
from app.api.routes.admin_unsourced import router as admin_unsourced_router
from app.api.routes.audit_log import router as audit_log_router
from app.api.routes.candidatures import router as candidatures_router
from app.api.routes.entreprise import router as entreprise_router
from app.api.routes.llm_tools import router as llm_tools_router
from app.api.routes.privacy import router as privacy_router
from app.api.routes.sources import router as sources_router
from app.api.routes.versioning import router as versioning_router
from app.auth.router import router as auth_router
from app.catalog.sources.router import router as catalog_sources_router
from app.chat.api import events_router as chat_events_router
from app.chat.api import router as chat_router
from app.core.rate_limit import limiter
from app.middleware.auth_session import AuthSessionMiddleware
from app.middleware.request_id import RequestIdMiddleware
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
# Request-ID middleware (F04 / FR-018) — runs before AuthSession.
app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*", "X-CSRF-Token"],
)

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(sources_router)
app.include_router(catalog_sources_router)
app.include_router(llm_tools_router)
app.include_router(admin_unsourced_router)
app.include_router(admin_llm_eval_router)
app.include_router(audit_log_router)
app.include_router(versioning_router)
app.include_router(candidatures_router)
app.include_router(privacy_router)
app.include_router(entreprise_router)
app.include_router(entreprise_router)
app.include_router(chat_router)
app.include_router(chat_events_router)

# F12 — Profile projets: CRUD + duplicate + transition + documents
from app.api.routes.projets import router as projets_router  # noqa: E402
from app.api.routes.projets_documents import router as projets_documents_router  # noqa: E402

app.include_router(projets_router)
app.include_router(projets_documents_router)

# F25 — Matching projet <-> offre (PME).
from app.matching.router import router as matching_router  # noqa: E402

app.include_router(matching_router)

# F27 — Simulateur de financement (PME, lecture seule).
from app.simulation.router import router as simulation_router  # noqa: E402

app.include_router(simulation_router)

# F26 — Generateur de dossiers de candidature (PME, MVP stub).
from app.dossier.router import router as dossier_router  # noqa: E402

app.include_router(dossier_router)

# F28 — Empreinte carbone (PME).
from app.carbon.router import router as carbon_router  # noqa: E402

app.include_router(carbon_router)

# F29 — Credit scoring (collecte + algorithme hybride source).
from app.credit.router import public_router as credit_public_router  # noqa: E402
from app.credit.router import router as credit_router  # noqa: E402

app.include_router(credit_router)
app.include_router(credit_public_router)

# F22 — Documents entreprise: upload / list / download / delete + OCR PDF natif.
from app.api.routes.entreprise_documents import router as entreprise_documents_router  # noqa: E402

# F50 — Extensions UI documents : fingerprint / validate / link-projet / relaunch.
from app.api.routes.entreprise_documents_f50 import (  # noqa: E402
    f50_router as entreprise_documents_f50_router,
    fingerprint_router as documents_fingerprint_router,
)

app.include_router(entreprise_documents_router)
app.include_router(documents_fingerprint_router)
app.include_router(entreprise_documents_f50_router)

# F10 — Admin support PME: read-only PME view (US1) + admin_view audit (US2).
# Must be registered BEFORE the generic CRUD wildcard /admin/{entity}/{id}.
from app.admin.routes.pme import router as admin_pme_router  # noqa: E402

app.include_router(admin_pme_router)

# F30 — Attestation verifiable (PME + admin + public).
from app.attestations.router import router as attestation_router  # noqa: E402

app.include_router(attestation_router)

# F06 — Back-office admin: register catalog entities, then mount generic routers.
from app import catalog as _catalog_registrations  # noqa: E402, F401, I001 — side-effect: registers entities

# NOTE: order matters — search/stats use literal paths under /admin and must be
# matched BEFORE the generic /admin/{entity}/{id} CRUD routes.
app.include_router(admin_search_router)
app.include_router(admin_stats_router)

# F08 — Catalog admin routers (Fonds, Intermediaire, Accreditation, Offre).
# Must be registered BEFORE the generic publish/CRUD routers so that the
# specialised paths under /admin/fonds, /admin/intermediaires, ... are not
# shadowed by the wildcard /admin/{entity}/...
from app.api.admin.accreditations import router as f08_acc_router  # noqa: E402
from app.api.admin.fonds import router as f08_fonds_router  # noqa: E402
from app.api.admin.intermediaires import router as f08_inter_router  # noqa: E402
from app.api.admin.offres import router as f08_offres_router  # noqa: E402

app.include_router(f08_fonds_router)
app.include_router(f08_inter_router)
app.include_router(f08_acc_router)
app.include_router(f08_offres_router)

# F09 — Catalog admin routers (Indicateur, Referentiel, Critere, DocumentRequis,
# FacteurEmission). Mounted before generic crud_router to avoid wildcard match.
from app.catalog.criteres.router import router as f09_criteres_router  # noqa: E402
from app.catalog.documents_requis.router import router as f09_documents_router  # noqa: E402
from app.catalog.facteurs_emission.router import router as f09_facteurs_router  # noqa: E402
from app.catalog.indicateurs.router import router as f09_indicateurs_router  # noqa: E402
from app.catalog.referentiels.router import router as f09_referentiels_router  # noqa: E402

app.include_router(f09_indicateurs_router)
app.include_router(f09_referentiels_router)
app.include_router(f09_criteres_router)
app.include_router(f09_documents_router)
app.include_router(f09_facteurs_router)

# F20 — Admin Skills CRUD (must be mounted BEFORE the generic admin_crud_router
# so /admin/skills/* is matched by the dedicated router, not the wildcard).
from app.admin.routes.skills import router as admin_skills_router  # noqa: E402

app.include_router(admin_skills_router)

app.include_router(admin_publish_router)
app.include_router(admin_crud_router)

# F19 — Skills engine internal endpoint (dev/test only).
from app.api.internal_skills import router as internal_skills_router  # noqa: E402

app.include_router(internal_skills_router)

# F23 — Scoring ESG multi-référentiels (PME).
from app.scoring.router import router as scoring_router  # noqa: E402

app.include_router(scoring_router)

# F24 — Rapport de conformité PDF (PME).
from app.rapports.router import router as rapports_router  # noqa: E402

app.include_router(rapports_router)

# F31 — Plan d'action ESG (PME).
from app.action_plan.routes import router as action_plan_router  # noqa: E402

app.include_router(action_plan_router)

# F32 — Dashboard PME (agrégat lecture seule + export "Mes données").
from app.dashboard.router import router as dashboard_router  # noqa: E402

app.include_router(dashboard_router)

# F33 — Extension Chrome : endpoints PME + admin.
from app.extension.admin_router import (  # noqa: E402
    router as extension_admin_router,
)
from app.extension.router import router as extension_router  # noqa: E402

app.include_router(extension_router)
app.include_router(extension_admin_router)

# F34 — Suivi candidatures PME + centre de notifications + recommandations.
from app.candidatures.router import (  # noqa: E402
    router as f34_me_candidatures_router,
)
from app.notifications.router import (  # noqa: E402
    router as f34_notifications_router,
)
from app.notifications.stream import (  # noqa: E402
    router as f38_notifications_stream_router,
)

app.include_router(f34_me_candidatures_router)
app.include_router(f34_notifications_router)
app.include_router(f38_notifications_stream_router)


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
