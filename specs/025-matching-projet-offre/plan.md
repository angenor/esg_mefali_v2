# Implementation Plan: F25 — Matching Projet ↔ Offre

**Branch**: `025-matching-projet-offre` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Backend MVP livrant le moteur de matching projet ↔ offre avec score décomposé fonds + intermédiaire (`min(fonds_score, intermediaire_score)`), endpoints PME pour lister/détailler, comparateur multi-intermédiaires et création de candidature avec snapshot F04. Frontend Nuxt et alertes/tool LLM reportés.

Pas de nouvelle table : on réutilise `projet`, `fonds_source`, `intermediaire`, `offre`, `accreditation`, `candidature` (déjà créée dans 0001).

## Technical Context

- **Language/Version**: Python 3.11 (backend)
- **Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2
- **Storage**: PostgreSQL 16 (réutilisation, pas de migration)
- **Testing**: Pytest + pytest-asyncio + httpx
- **Target Platform**: Backend Linux
- **Performance Goals**: matching 100 offres < 1s P95
- **Constraints**: Plateforme fermée PME + Admin, RLS active, audit append-only, Money typé FCFA-EUR 655.957
- **Scale/Scope**: ~50 offres MVP, ~10 PME démo

## Constitution Check

Tous les gates passent (cf. spec §7).

## Project Structure

```text
backend/
├── app/
│   ├── matching/                    # NEW
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── heuristics.py
│   │   ├── service.py
│   │   ├── candidature_service.py
│   │   └── router.py
│   └── main.py                      # MODIFIED: include router
└── tests/
    ├── unit/matching/
    └── integration/matching/

specs/025-matching-projet-offre/
├── spec.md
├── plan.md
├── tasks.md
└── contracts/
```

**Structure Decision** : nouveau package `app/matching/` (cohérent avec `app/scoring/`, `app/projets/`).

## Phase 0 — Research

- **Pas de migration** : tout existe déjà.
- **Money** : `app/utils/money.py` taux fixe 655.957.
- **Snapshot** : construction inline simple + SHA-256 `hashlib`.
- **RLS** : `Depends(get_current_pme)` (cohérent F12).
- **Tri** : `ORDER BY min(fonds_score, intermediaire_score) DESC, fonds_score DESC`.

## Phase 1 — Design

### Endpoints

```
GET  /me/projets/{projet_id}/matching?limit=10
GET  /me/projets/{projet_id}/matching/{offre_id}
GET  /me/fonds/{fonds_id}/intermediaires-comparator?projet_id={uuid}&limit=5
POST /me/projets/{projet_id}/candidatures   body {offre_id}
```

### Erreurs standardisées

| Code | HTTP |
|------|------|
| `projet_not_found` | 404 |
| `offre_not_found` | 404 |
| `no_active_accreditation` | 409 |
| `validation_error` | 422 |

## Phase 2 — Tasks

Voir [tasks.md](./tasks.md).

## Complexity Tracking

Aucune violation.
