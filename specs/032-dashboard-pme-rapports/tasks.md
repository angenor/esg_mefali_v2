# Tasks — F32 Dashboard PME (MVP backend)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## T01 — Schémas Pydantic
- Fichier : `backend/app/dashboard/schemas.py`
- `ScoreEntry`, `CarbonEntry`, `CreditScoreEntry`, `CandidatureItem`, `CandidatureBlock`, `RapportBlock`, `AttestationBlock`, `ActionStepEntry`, `DashboardSummaryOut`, `DataExportOut`.

## T02 — Service `build_summary`
- Fichier : `backend/app/dashboard/service.py`
- Requêtes SQLAlchemy ORM/text scope `account_id`.
- Limite top 5 partout.

## T03 — Service `build_export`
- Même fichier que T02.
- Agrège toutes les tables du compte courant en JSON.

## T04 — Router
- Fichier : `backend/app/dashboard/router.py`
- `GET /me/dashboard/summary` → `DashboardSummaryOut`.
- `GET /me/data/export` → `DataExportOut`.
- Best-effort audit log via `record_audit`.

## T05 — Wiring
- `backend/app/main.py` : `include_router(dashboard_router)`.

## T06 — Tests RLS + audit
- `backend/tests/dashboard/test_dashboard_summary.py`.
- `backend/tests/dashboard/test_data_export.py`.

## T07 — Lint + couverture ≥ 80 % sur les nouveaux modules.
