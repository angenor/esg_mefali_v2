# Implementation Plan: F12 — Profil → Projets

**Branch**: `main` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Livrer la vue Profil → Projets côté PME : CRUD projets enrichis (objectif environnemental, types_impact[], maturité, montant_recherche Money typé, durée, structure_financement[], indicateurs_impact_json, localisation projet, statut workflow), duplication, suppression soft, transitions de statut, et upload de documents projet (whitelist mime, taille ≤ 25 MB, ≤ 50 docs/projet) avec abstraction `Storage` (LocalStorage MVP). Audit per-field append-only, versioning optimiste (If-Match), RLS multi-tenant, events SSE temps réel — strictement aligné sur F11.

## Technical Context

- **Language/Version**: Python 3.11 (backend), TypeScript 5.x / Node 20 (frontend)
- **Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 (existant)
- **Storage**: PostgreSQL 16 + pgvector ; filesystem local pour fichiers (`backend/storage/`)
- **Testing**: Pytest + pytest-asyncio + httpx (backend)
- **Target Platform**: Backend Linux, Frontend SSR + SPA
- **Performance**: Upload 10 MB < 5 s ; liste paginée < 300 ms P95
- **Constraints**: RLS, audit append-only, money typé, versioning, plateforme fermée

## Constitution Check

Voir `spec.md §Constitution Check`. Tous gates passés. Pas d'amendement.

## Project Structure

```text
specs/012-profile-projets/
├── plan.md
├── spec.md
└── tasks.md

backend/
├── alembic/versions/
│   └── 0012_f12_projets_documents.py
├── app/
│   ├── projets/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── documents_service.py
│   │   ├── events.py
│   │   └── validators.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── local.py
│   └── api/routes/
│       ├── projets.py
│       └── projets_documents.py
└── tests/
    └── projets/
        ├── test_migration.py
        ├── test_service.py
        ├── test_documents.py
        ├── test_routes.py
        └── test_rls.py
```

## Phase 0 — Research

- Réutilisation du pattern F11 (`entreprise/service.py`) pour audit + versioning + events SSE.
- Storage : couche minimale Protocol (`save`, `read`, `delete`, `exists`).
- RLS : `document_projet` ajoutée à la liste RLS dans la migration.

## Phase 1 — Design

- **schemas** : `ProjetRead`, `ProjetCreate`, `ProjetPatch`, `ProjetSummary`, `Money`,
  `IndicateurImpact`, `DocumentProjetRead`, `TransitionIn`, `ConflictOut`.
- **service** : `list_projets`, `get_projet`, `create_projet`, `patch_projet`, `duplicate_projet`,
  `delete_projet`, `transition_projet`. Tous via `record_audit`.
- **documents_service** : `upload_document`, `list_documents`, `read_document`, `delete_document`.
- **storage.base.Storage** : Protocol — `save`, `read`, `delete`, `exists`.
- **events** : `publish`, `subscribe`.
- **validators** : `validate_indicateurs`, `validate_mime`, `validate_size`.
- **routes** : voir spec.md FR-002, FR-005.

## Phase 2 — Tasks

Voir `tasks.md`.

## Complexity Tracking

> Aucune violation.
