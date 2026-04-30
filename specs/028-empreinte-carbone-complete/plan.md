# Implementation Plan F28 — Empreinte Carbone (MVP)

**Branch**: `028-empreinte-carbone-complete` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Backend-only MVP : moteur de calcul d'empreinte carbone (somme `valeur * facteur F09`),
table `carbon_footprint`, endpoints PME, plan de réduction stub. Frontend, US1 questionnaire complet,
US7 tool LLM, US4 viz F15/F16 → `[DEFERRED]`.

## Technical Context

- **Language**: Python 3.11 (backend FastAPI). Pas de frontend en MVP.
- **Storage**: PostgreSQL 16 (existant), pgvector inutilisé.
- **Tests**: pytest + pytest-asyncio + httpx.
- **Dépendances** : F03 (sources verified), F09 (`facteur_emission`), F11 (entreprise), F02 (auth + RLS), F04 (record_audit).

## Constitution Check

| # | Principe | Status |
|---|----------|--------|
| P1 | Sourçage anti-hallucination | OK chaque facteur référence `source_id` F09. |
| P2 | RLS multi-tenant | OK `account_id` filtré, GET par account propriétaire. |
| P3 | Audit append-only | OK `record_audit('carbon_footprint','compute', ...)`. |
| P4 | Versioning | OK snapshot `factor_versions_json`. |
| P5 | Money typé | N/A en MVP (plan stub n'utilise pas Money). |
| P6 | Pivot indicateur unique | OK pas de mutation indicateurs. |
| P7 | Plateforme fermée | OK endpoints `/me/carbon/*` PME-only. |
| P8-10 | N/A | OK |

## Phase 0 — Research

- **Lookup facteur** : `SELECT * FROM facteur_emission WHERE code=:c AND (pays_iso2=:p OR pays_iso2 IS NULL) AND status='published' AND valid_from_date <= :ref ORDER BY pays_iso2 NULLS LAST, version DESC LIMIT 1`.
- **Conversion** : valeur facteur en `kgCO2e/<unite>` * quantité / 1000 = tCO2e.
- **Audit** : réutilisation `app/audit/recorder.record_audit`.

## Phase 1 — Design

```
backend/app/carbon/
  __init__.py
  engine.py        # fonctions pures: compute_line, compute_total
  plan.py          # bibliothèque actions inline + generate_plan
  service.py       # CarbonService (orchestre db + audit)
  schemas.py       # Pydantic
  router.py        # 3 endpoints

backend/app/models/carbon_footprint.py
backend/alembic/versions/028_carbon_footprint.py
backend/tests/unit/carbon/test_engine.py
backend/tests/unit/carbon/test_plan.py
backend/tests/integration/carbon/test_router.py
```

## Phase 2 — Tasks

Voir [tasks.md](./tasks.md).

## Complexity Tracking

Aucune violation.
