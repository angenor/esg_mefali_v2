# Implementation Plan: F32 — Dashboard PME (MVP backend agrégateur)

**Branch**: `032-dashboard-pme-rapports` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Livrer 2 endpoints PME en lecture seule : `GET /me/dashboard/summary` (agrégat optimisé) et `GET /me/data/export` (export JSON complet du compte). Aucune nouvelle table. Réutilisation stricte des modèles existants (F23/F24/F25/F28/F29/F30/F31). Audit append-only via le helper `record_audit` existant (F04).

## Technical Context

- **Language**: Python 3.11
- **Framework**: FastAPI + SQLAlchemy 2.x
- **DB**: PostgreSQL 16 + RLS (F02)
- **Tests**: pytest + httpx TestClient
- **Auth**: `get_current_pme` dependency (F02)
- **Audit**: `record_audit` (F04)

## Constitution Check

| # | Principle | Application | Status |
|---|-----------|-------------|--------|
| P1 | Sourçage anti-hallucination | Pas de nouvelle donnée factuelle, seulement agrégation. | OK |
| P2 | RLS multi-tenant | Toutes les requêtes filtrent par `user.account_id`. | OK |
| P3 | Audit append-only | `record_audit` invoqué pour chaque endpoint. | OK |
| P4 | Versioning candidatures | N/A — lecture seule. | OK |
| P5 | Money typé | N/A. | OK |
| P7 | Plateforme fermée | Endpoints `/me/*` PME-only. | OK |

## Project Structure

```text
backend/app/dashboard/
├── __init__.py
├── service.py
├── schemas.py
└── router.py

backend/tests/dashboard/
├── __init__.py
├── conftest.py
├── test_dashboard_summary.py
└── test_data_export.py
```

## Phase 0 — Research

- Modèles inspectés : `ScoreCalculation`, `Attestation`, `CreditScore`, `CarbonFootprint`, `ActionStep`. Tables sans SQLAlchemy model lues via SQL : `candidature`, `rapport_conformite`, `consent`.
- Pattern `get_current_pme` confirmé dans `app/api/routes/privacy.py`.
- Pattern `record_audit` confirmé dans F23/F30.
- Fixtures de test : `client`, `unique_email`, `valid_password` de `tests/integration/conftest.py`.

## Phase 1 — Design

### Endpoints

```
GET /me/dashboard/summary -> DashboardSummaryOut
GET /me/data/export       -> DataExportOut
```

### DashboardSummaryOut (Pydantic)

- `scores: list[ScoreEntry]` (latest par référentiel)
- `carbon: list[CarbonEntry]` (latest par année)
- `credit_score: CreditScoreEntry | None`
- `candidatures: CandidatureBlock` (counters_by_statut + recent[<=5])
- `rapports: RapportBlock` (total + recent[<=5])
- `attestations: AttestationBlock` (active + revoked + recent[<=5])
- `next_actions: list[ActionStepEntry]` (<=5 non clos, ordre due_at asc)

### DataExportOut

`account`, `entreprise`, `projets`, `candidatures`, `scores`, `carbon`, `credit_score`, `rapports`, `attestations`, `consents`, `action_plan`, `exported_at` (ISO-8601 UTC).

### Audit

`record_audit(entity_type='account', entity_id=account_id, action='dashboard_view'|'data_export', source_of_change='manual', actor_user_id=user.id)` — best-effort wrapper try/except.

## Phase 2 — Tasks

Voir [tasks.md](./tasks.md).

## Complexity Tracking

Aucune dérogation. Pas de migration.
