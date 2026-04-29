# Implementation Plan: Profil Entreprise — édition manuelle synchronisée LLM

**Branch**: `011-11-profile-entreprise` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Couche backend du profil entreprise PME : enrichissement de la table `entreprise` (ajout colonnes `secteur_code`, `secteur_label`, `localisation_siege_pays_iso2`, `localisation_siege_ville`, `zones_operation_pays_iso2[]`, `gouvernance_json`, contrainte UNIQUE `account_id`), endpoints REST `GET/PUT/PATCH /me/entreprise` avec optimistic concurrency `If-Match`/`version` + audit log par champ, endpoint complétude `GET /me/entreprise/completeness`, endpoint taxonomie `GET /me/entreprise/sectors`, et canal SSE `GET /me/entreprise/events` pour la synchro temps réel. Validation Pydantic v2 stricte avec money typé et pays ISO2 UEMOA/CEDEAO. La provenance par champ est calculée à partir de `audit_log` (F04) — aucune nouvelle table dédiée à la provenance.

## Technical Context

- **Language**: Python 3.11 backend ; TypeScript 5 / Nuxt 4 frontend (UI deferred).
- **Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2.
- **Storage**: PostgreSQL 16 + pgvector (RLS active via `app.current_account_id`).
- **Testing**: Pytest + httpx (backend).
- **Performance Goals**: GET < 200ms p95 ; PATCH < 500ms p95 ; SSE push < 1s.
- **Constraints**: invariants Module 0 (sourcing, RLS, audit append-only, version, money typé, peg FCFA-EUR 655.957, plateforme PME/Admin, bottom sheet UI).
- **Scale**: 1 entreprise par account ; ~10k comptes en cible.

## Constitution Check

| # | Principe | Gate | Status |
|---|---|---|---|
| P1 | Sourçage anti-hallucination | Mutations manuelles → `manual` ; mutations LLM-tool → `llm` (enum existant). | ok |
| P2 | Multi-tenant RLS | Endpoints `/me/entreprise/*` filtrent par `account_id` via RLS Postgres. | ok |
| P3 | Audit append-only | Chaque PATCH/PUT produit N enregistrements (un par champ modifié) via `record_audit`. | ok |
| P4 | Versioning | `entreprise.version` int ; contrôle `If-Match`. | ok |
| P5 | Money typé | `taille_ca_amount` + `taille_ca_currency` ; devises {XOF, EUR, USD}. | ok |
| P6 | Pivot Indicateur unique | N/A. | ok |
| P7 | Plateforme fermée | Endpoints sous `/me/...` requièrent `get_current_pme`. | ok |
| P8 | Édition manuelle + sync LLM | Cœur de la feature ; SSE pour push. | ok |
| P9 | Tool-use LLM fiable | API stable consommable par `update_company_profile` (F17). | ok |
| P10 | UX bottom sheet | Frontend différé. | ok |

## Project Structure

```text
specs/011-11-profile-entreprise/
├── spec.md
├── plan.md
├── tasks.md
└── checklists/requirements.md

backend/
├── alembic/versions/0010_f11_entreprise_enrich.py
├── app/
│   ├── api/routes/entreprise.py          # endpoints GET/PUT/PATCH /me/entreprise
│   ├── entreprise/
│   │   ├── __init__.py
│   │   ├── service.py                    # get_or_provision, update_partial, put_full
│   │   ├── schemas.py                    # Pydantic v2 IN/OUT
│   │   ├── taxonomy.py                   # liste sectors + countries UEMOA/CEDEAO
│   │   ├── completeness.py               # matrice features→champs déclarative
│   │   ├── provenance.py                 # agrégation audit_log → meta par champ
│   │   └── events.py                     # SSE in-process pub/sub
│   └── models/entreprise.py              # ORM model
└── tests/
    ├── unit/entreprise/
    │   ├── test_taxonomy.py
    │   ├── test_completeness.py
    │   ├── test_provenance.py
    │   └── test_schemas.py
    └── integration/entreprise/
        ├── test_entreprise_get.py
        ├── test_entreprise_patch.py
        ├── test_entreprise_put_ifmatch.py
        ├── test_entreprise_completeness.py
        ├── test_entreprise_sectors.py
        ├── test_entreprise_rls.py
        └── test_entreprise_audit.py
```

## Migration alembic 0010_f11_entreprise_enrich

Non destructive. Ajoute :
- `entreprise.secteur_code TEXT NULL`
- `entreprise.secteur_label TEXT NULL`
- `entreprise.localisation_siege_pays_iso2 CHAR(2) NULL`
- `entreprise.localisation_siege_ville TEXT NULL`
- `entreprise.zones_operation_pays_iso2 TEXT[] NULL`
- `entreprise.gouvernance_json JSONB NULL`
- `UNIQUE (account_id)` (sera ajouté seulement si pas déjà présent ; ABORT si doublons existants)
- index pour les jointures futures (`ix_entreprise_secteur_code`).

Conserve les colonnes historiques (`secteur TEXT`, `localisation TEXT`, `gouvernance TEXT`) — aucune suppression.

## Endpoints

| Méthode | Chemin | Rôle | Description |
|---|---|---|---|
| GET | /me/entreprise | pme | Lit profil + métadonnées par champ. Provisionne row si absente. |
| PUT | /me/entreprise | pme | Édition complète. Header If-Match. 200/409/422. |
| PATCH | /me/entreprise | pme | Édition partielle. Header If-Match. 200/409/422. |
| GET | /me/entreprise/completeness | pme | % et champs manquants par feature aval. |
| GET | /me/entreprise/sectors | pme | Liste taxonomie sectorielle (~50 codes). |
| GET | /me/entreprise/events | pme | SSE stream des updates (canal account-scope). |

## Risques

- Si `account_id` UNIQUE n'est pas présent et qu'il existe déjà des doublons, la migration ABORT proprement (test pré-migration). Aucune destruction.
- SSE in-process : pas de scaling multi-process (acceptable pour 1 worker MVP).
- F18 doit relire l'entreprise à chaque tour LLM ; non livré ici, mais aucune dépendance bloquante (assumption).

## Hors-scope (this session)

- Page Nuxt `/profil/entreprise` (UI US1/US2) — backend complet, page deferred.
- LLM tool `update_company_profile` (livré en F17).
- Test contractuel cross-language zod ↔ Pydantic.
