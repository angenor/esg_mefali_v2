# Implementation Plan: F31 — Plan d'Action ESG (MVP)

**Branch**: `031-plan-action-rappels-bibliotheque` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/031-plan-action-rappels-bibliotheque/spec.md`

## Summary

Livrer le squelette backend du **Plan d'Action ESG personnalisé** : deux nouvelles tables (`action_plan`, `action_step`) avec RLS strict, un service `ActionPlanService` qui transforme les lacunes du dernier `ScoreCalculation` (F23) en étapes priorisées, et trois endpoints HTTP `/me/action-plan*` (POST generate, GET, PATCH step). Aucun frontend, aucun cron, aucune notification, aucune bibliothèque de ressources, aucun tool LLM en MVP — tout est explicitement reporté en `[DEFERRED]`. Audit et RLS réutilisent les briques existantes (F02 + F04). Génération déterministe, idempotente sur le `ScoreCalculation` source, versionnée par `version = max+1`.

## Technical Context

**Language/Version**: Python 3.11 (backend uniquement)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2
**Storage**: PostgreSQL 16 (réutilisation de la base, RLS via politiques `account_id` héritées du pattern F02)
**Testing**: pytest + pytest-asyncio + httpx (TestClient FastAPI)
**Target Platform**: Linux (hébergement Europe ou Afrique de l'Ouest)
**Project Type**: Web service backend (monorepo, dossier `backend/`)
**Performance Goals**: Génération d'un plan < 2 s P95, GET plan < 200 ms P95
**Constraints**: RLS strict, audit append-only, plateforme fermée PME + Admin, langue FR
**Scale/Scope**: ~10k comptes PME, ~10–30 étapes par plan, 2 tables nouvelles, 3 endpoints, 1 migration Alembic

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question pour cette feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Aucune donnée factuelle nouvelle (catalogue). Les étapes générées s'appuient sur des indicateurs déjà sourcés F23/F03. `action_step.source_id` (nullable) prévu pour enrichissement post-MVP. | ✅ |
| P2 | Multi-tenant RLS | `action_plan` et `action_step` portent `account_id` (direct ou via plan), avec politiques RLS `USING (account_id = current_setting('app.current_account_id'))`. Cross-tenant → 404. | ✅ |
| P3 | Audit log append-only | Génération + PATCH step appellent `record_audit` (F04) avec `source_of_change='manual'` (PME). Régénération produit version+1, jamais d'UPDATE destructif. | ✅ |
| P4 | Versioning + snapshot candidatures | `action_plan.version` (int) + `score_calculation_id` (snapshot du calcul source). Pas de candidatures impactées. | ✅ |
| P5 | Money typé | N/A — aucune valeur monétaire dans le MVP (coûts/bénéfices déférés). | ✅ |
| P6 | Pivot Indicateur unique | `action_step.indicateur_id` (FK nullable vers `indicateur`) — pas de duplication par axe ou par référentiel. | ✅ |
| P7 | Plateforme fermée | Endpoints sous `/me/*` (PME uniquement, role `pme`). Pas de rôle nouveau, pas de sortie externe. | ✅ |
| P8 | Édition manuelle + sync LLM | Le statut et `responsible_user_id` sont éditables manuellement. Pas de champ LLM-alimenté en MVP. | ✅ |
| P9 | Tool-use LLM fiable | N/A — aucun tool LLM nouveau (US8 différée). | ✅ |
| P10 | UX bottom sheet | N/A — pas de frontend en MVP. | ✅ |

**Verdict** : tous les gates passent ou sont N/A. Pas d'amendement constitutionnel requis.

### Contraintes techniques rappelées

- Backend Python 3.11 dans `.venv`, Postgres seul service dockerisé.
- Hébergement Europe / Afrique de l'Ouest uniquement.
- Langue : français pour les libellés générés (titres d'étapes, descriptions).
- Pas de Redis, pas de cron, pas de queue : exécution synchrone HTTP.
- Pattern RLS : `SET LOCAL app.current_account_id = '<uuid>'` par requête (pattern F02 déjà en place).

## Project Structure

### Documentation (this feature)

```text
specs/031-plan-action-rappels-bibliotheque/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── action-plan-api.yaml  # OpenAPI 3.1 fragment
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── action_plan/                       # NEW module
│   │   ├── __init__.py
│   │   ├── routes.py                      # POST /me/action-plan/generate, GET /me/action-plan, PATCH /me/action-plan/steps/{id}
│   │   ├── service.py                     # ActionPlanService.generate(), get_current(), update_step()
│   │   ├── generator.py                   # GapAnalyzer + StepFactory (algo déterministe)
│   │   ├── schemas.py                     # Pydantic v2: ActionPlanRead, ActionStepRead, ActionStepPatch, GenerateRequest
│   │   └── enums.py                       # Category, Priority, StepStatus, Horizon
│   ├── models/
│   │   ├── action_plan.py                 # NEW
│   │   └── action_step.py                 # NEW
│   └── main.py                            # include router
├── alembic/versions/
│   └── 0021_f31_action_plan.py            # action_plan + action_step tables + RLS policies
└── tests/
    ├── unit/action_plan/
    │   ├── test_generator.py              # algo déterministe
    │   ├── test_service.py                # versioning, RLS unit
    │   └── test_schemas.py                # validation enums
    ├── integration/action_plan/
    │   ├── test_generate_endpoint.py
    │   ├── test_get_endpoint.py
    │   ├── test_patch_step_endpoint.py
    │   └── test_rls_isolation.py
    └── contract/action_plan/
        └── test_openapi_contract.py
```

**Structure Decision** : Web service backend, structure monorepo existante. Module dédié `app/action_plan/` cohérent avec les modules feature-domain existants (`app/scoring`, `app/credit`, `app/carbon`, etc.). Pas de frontend.

## Phase 0 — Research

Voir [research.md](./research.md). Décisions clés :

- **Algo de génération** : déterministe à partir des indicateurs en lacune extraits du `ScoreCalculation.details_json` du dernier calcul ; mapping severity → priority ; titre/description templatés en FR.
- **Concurrence** : verrou applicatif via `SELECT ... FOR UPDATE` sur la dernière `action_plan` de l'account, pour calculer `version = max+1` sans race.
- **RLS** : pattern F02 réutilisé tel quel — `SET LOCAL app.current_account_id` côté middleware existant.
- **Audit** : `record_audit(table, row_id, action, before, after, source_of_change='manual', user_id, account_id)` pour generate + patch_step.
- **Étape par défaut** : si zéro lacune détectée, une étape "Revue annuelle ESG" est créée (catégorie `esg`, priorité `moyenne`, horizon `+12 mois`).
- **Dépendance F23** : lecture de `ScoreCalculation` la plus récente côté `account_id` ; si aucune, 422.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) : schéma SQL `action_plan` + `action_step`, contraintes, enums, politiques RLS.
- [contracts/action-plan-api.yaml](./contracts/action-plan-api.yaml) : OpenAPI 3.1 fragment pour les 3 endpoints.
- [quickstart.md](./quickstart.md) : pas-à-pas validation locale (migration, génération, GET, PATCH).
- Mise à jour de `CLAUDE.md` (référence plan).

## Complexity Tracking

> Aucune violation. Section vide.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
