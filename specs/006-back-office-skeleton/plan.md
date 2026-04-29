# Implementation Plan: F06 — Squelette Back-Office Admin & Workflow draft → published

**Branch**: `006-back-office-skeleton` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-back-office-skeleton/spec.md`

## Summary

Livrer le squelette back-office Admin (`/admin/*`) commun à toutes les features de catalogue ultérieures (F07, F08, F09, F10, F20). F06 fournit :

- côté FastAPI : middleware admin (vérif rôle + pose `app.is_admin = true`), routeur générique CRUD `/admin/{entity}/`, endpoint `/publish` qui valide les sources `verified` et écrit `audit_log` (F04), endpoints `/search` et `/stats/catalog`, registry d'entités catalogue extensible.
- côté Nuxt 4 : layout `admin.vue` (sidebar, header, breadcrumbs, palette dédiée, pas de gsap), middleware route `role==='admin'`, composables `useEntityCrud<T>`, `useAdminDraft` (localStorage debounce 1.5s), composants `<AdminListPage>`, `<AdminFormPage>`, `<StatusBadge>`, `<VersionTimeline>`, `<AdminSearchBar>`.
- contrats partagés : pagination cursor-based, optimistic locking via `If-Match` (réutilise F04), audit `source_of_change='admin'`, gate de publication = toutes sources `verified`.

Aucune entité catalogue concrète n'est livrée ici (rails uniquement). Une **entité de démonstration `demo_indicator`** est introduite uniquement pour valider end-to-end le pattern (workflow draft→published, versioning, audit, sources gate) — purement interne, supprimable à F09 quand `Indicateur` réel arrive.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend Nuxt 4)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2 (`extra='forbid'`), Alembic ; Nuxt 4 (Composition API), Pinia, TailwindCSS v4, VueUse (`useDebounceFn`, `useStorage`)
**Storage**: PostgreSQL 16 + pgvector (RLS active F02). Aucune nouvelle table métier ; une seule migration ajoute `demo_indicator` (entité catalogue de démo) + index trigram pour `/admin/search`
**Testing**: pytest + httpx (backend, contract + integration), Vitest + @nuxt/test-utils (frontend unit/component), Playwright (E2E `/admin` flows)
**Target Platform**: Web (Nuxt 4 SSR + FastAPI) ; déploiement Europe/Afrique de l'Ouest
**Project Type**: Web application (backend + frontend)
**Performance Goals**: `/admin/{entity}` list p95 < 300 ms (75 lignes paginées), `/admin/stats/catalog` p95 < 500 ms (catalogue ≤ 10 000 objets), `/admin/search` p95 < 400 ms (trigram), 100+ admins simultanés
**Constraints**: Pagination obligatoire ≥ 50 lignes ; offline-friendly draft (localStorage debounce 1.5 s) ; palette admin distincte (aucune fuite CSS PME) ; accessibilité clavier complète ; français only MVP
**Scale/Scope**: 8+ types de catalogue à venir (Sources, Fonds, Intermédiaires, Offres, Référentiels, Indicateurs, Critères, Documents requis, Templates, Skills, Facteurs d'émission, PME, Métriques) ; ~12 sections sidebar

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F06 ne crée aucune entité factuelle ESG. L'endpoint `/publish` impose toutes sources `verified` sinon 422 ; l'entité de démo `demo_indicator` porte `source_id NOT NULL`. | ✅ |
| P2 | Multi-tenant RLS | Le middleware admin pose `app.is_admin = true` mais conserve `app.current_account_id` ; `demo_indicator` est une table catalogue (pas tenant) sans `account_id` requis (politique RLS = lecture publique authentifiée + écriture admin), conforme à la convention F01. | ✅ |
| P3 | Audit log append-only | Toutes les mutations `/admin/{entity}/*` (POST/PUT/publish) écrivent `audit_log` avec `source_of_change='admin'` via helper F04. Échec → rollback transactionnel global. | ✅ |
| P4 | Versioning + snapshot | L'endpoint `/publish` réutilise `publish_new_version` + `If-Match` de F04 ; toute édition d'objet `published` crée v2 immuable. | ✅ |
| P5 | Money typé | F06 ne manipule aucune valeur monétaire (squelette). Si une entité catalogue future expose un `Money`, F06 ne contraint pas le type — c'est délégué aux features F07-F20. | ✅ |
| P6 | Pivot Indicateur unique | F06 ne saisit aucune valeur PME. `demo_indicator` reste un objet catalogue (modèle), aucune réponse PME stockée. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | F06 ne crée aucun rôle utilisateur supplémentaire — uniquement `admin` (déjà F02). Aucun webhook/push externe. | ✅ |
| P8 | Édition manuelle + sync LLM | Tous les champs catalogue introduits par F06 sont éditables manuellement par défaut (c'est le but du back-office). Pas de champ LLM-only. | ✅ |
| P9 | Tool-use LLM fiable | F06 n'expose aucun tool LLM. Hors scope. | ✅ |
| P10 | UX bottom sheet | Le back-office est une zone admin distincte, pas une UI conversationnelle. La règle bottom-sheet ne s'y applique pas (constitution P10 vise les composants interactifs en discussion LLM). Aucune fuite vers la UI PME. | ✅ |

Aucun écart à justifier. Pas de complexité non standard.

### Contraintes techniques (rappel)

- Stack imposée respectée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; no Docker backend dev (`.venv`), `pnpm dev` front.
- Hébergement Europe/Afrique de l'Ouest, langue FR par défaut.
- Aucun secret hardcodé ; pas de nouvelles variables d'env requises.

## Project Structure

### Documentation (this feature)

```text
specs/006-back-office-skeleton/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── admin-entity-crud.openapi.yaml
│   ├── admin-publish.openapi.yaml
│   ├── admin-search.openapi.yaml
│   └── admin-stats.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md  # produced by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── admin/                     # NEW — package back-office
│   │   ├── __init__.py
│   │   ├── middleware.py          # ensure_admin + set app.is_admin
│   │   ├── registry.py            # EntityRegistry (extensible par F07+)
│   │   ├── crud_router.py         # generic FastAPI router factory
│   │   ├── publish.py             # publish workflow (sources_verified gate)
│   │   ├── search.py              # /admin/search ILIKE/trigram
│   │   ├── stats.py               # /admin/stats/catalog
│   │   ├── pagination.py          # cursor-based helpers
│   │   ├── etag.py                # If-Match optimistic locking
│   │   └── schemas/
│   │       ├── pagination.py
│   │       ├── publish.py
│   │       └── search.py
│   ├── catalog/
│   │   └── demo_indicator.py      # NEW — entité de démonstration F06
│   ├── audit/                     # F04 (existant) — helper write_admin_event
│   └── main.py                    # mount /admin router
├── alembic/versions/
│   └── 20260429_F06_demo_indicator.py
└── tests/
    ├── contract/admin/
    │   ├── test_crud_contract.py
    │   ├── test_publish_contract.py
    │   ├── test_search_contract.py
    │   └── test_stats_contract.py
    ├── integration/admin/
    │   ├── test_admin_middleware.py
    │   ├── test_publish_flow.py        # full demo_indicator draft→published
    │   ├── test_etag_concurrency.py
    │   ├── test_audit_admin.py
    │   └── test_pagination_cursor.py
    └── unit/admin/
        ├── test_registry.py
        ├── test_pagination_helpers.py
        └── test_publish_gate.py

frontend/
├── layouts/
│   └── admin.vue                  # NEW
├── middleware/
│   └── admin.global.ts            # ou admin.ts route-scoped
├── pages/admin/
│   ├── index.vue
│   └── [entity]/
│       ├── index.vue              # liste générique
│       └── [id].vue               # form générique (create/edit)
├── components/admin/
│   ├── AdminListPage.vue
│   ├── AdminFormPage.vue
│   ├── StatusBadge.vue
│   ├── VersionTimeline.vue
│   └── AdminSearchBar.vue
├── composables/
│   ├── useEntityCrud.ts
│   ├── useAdminDraft.ts           # localStorage debounce 1.5s
│   └── useAdminStats.ts
├── assets/styles/admin.css        # palette dédiée, isolée de PME
└── tests/
    ├── unit/composables/
    │   ├── useEntityCrud.spec.ts
    │   └── useAdminDraft.spec.ts
    ├── component/admin/
    │   ├── StatusBadge.spec.ts
    │   ├── AdminListPage.spec.ts
    │   ├── AdminFormPage.spec.ts
    │   └── VersionTimeline.spec.ts
    └── e2e/
        ├── admin-access-403.spec.ts
        ├── admin-publish-demo.spec.ts
        └── admin-versioning.spec.ts
```

**Structure Decision**: Web application (Option 2) — backend FastAPI + frontend Nuxt 4 séparés. F06 introduit deux nouveaux packages (`backend/app/admin/` et `frontend/components/admin/`) qui seront étendus (jamais réécrits) par F07-F10, F20. Le registry d'entités est le point d'extension — chaque future feature catalogue déclare ses entités via `EntityRegistry.register(EntitySpec(...))`.

## Phase 0 — Research

Voir [research.md](./research.md). Sujets clés :

1. Pattern FastAPI router factory pour CRUD générique typé Pydantic (registry-based vs subclass).
2. Cursor-based pagination en SQLAlchemy 2.x (keyset sur `(created_at, id)` opaque base64).
3. Optimistic locking via `If-Match`/ETag réutilisant `version` F04 (cohérence multi-features).
4. PostgreSQL `pg_trgm` pour `/admin/search` (index GIN sur champs texte des tables catalogue).
5. Nuxt 4 layouts isolés (CSS scoping, pas de fuite Tailwind PME).
6. localStorage debounce + reprise (VueUse `useStorage` + `useDebounceFn`, conflit serveur).
7. Palette admin (densité informationnelle, contraste WCAG AA).

## Phase 1 — Design & Contracts

Voir [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).

Livrables Phase 1 :

- `data-model.md` : schéma `demo_indicator` (id, name, description, status enum, source_id NOT NULL, version, valid_from, valid_to, created_at, updated_at, created_by, published_by) + index trigram + politique RLS `is_admin or status='published'`.
- `contracts/` : 4 fragments OpenAPI (CRUD générique paramétrable par `{entity}`, publish, search, stats) avec exemples de pagination cursor et `If-Match`.
- `quickstart.md` : marche-à-suivre dev local pour démarrer le back-office, créer un demo_indicator, lier une source verified, publier, vérifier audit_log et version v2.

Re-check Constitution post-Phase 1 : aucun changement, gates restent ✅.

## Complexity Tracking

Aucune violation. Pas d'écart constitutionnel à justifier.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (n/a) | (n/a) | (n/a) |
