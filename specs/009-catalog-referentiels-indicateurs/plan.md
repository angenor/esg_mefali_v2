# Implementation Plan: F09 — Catalogue Référentiels, Indicateurs, Critères, Documents Requis, Facteurs d'Émission

**Branch**: `009-catalog-referentiels-indicateurs` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/009-catalog-referentiels-indicateurs/spec.md`

## Summary

Livrer la couche atomique du modèle ESG : 5 entités catalogue (`indicateur`, `referentiel`+`referentiel_indicateur`, `critere`, `document_requis`, `facteur_emission`), CRUD complet `/admin` via le `crud_router` F06, sourcing obligatoire (Invariant Module 0), versioning + audit (F04), RLS catalogue global (politique alternative comme F08), validateur de cohérence Référentiel et évaluateur DSL JSON sandboxé. Helpers serveur `get_referentiel(code, version?)` et `get_facteur(code, pays?, at?)` pour consommation par F23/F28. Page admin Référentiel /full + bottom sheet UX. Implémentation FastAPI + SQLAlchemy + Alembic + Pydantic + Postgres ; Nuxt 4 admin pages.

## Technical Context

**Language/Version**: Python 3.12 (backend, venv) ; TypeScript 5 + Nuxt 4 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, asyncpg, Nuxt 4, pnpm
**Storage**: PostgreSQL 16 + pgvector ; embeddings Voyage `voyage-3.5` (1024 dim) — non utilisés directement par F09 mais le pipeline reste compatible
**Testing**: pytest + pytest-asyncio + httpx (backend) ; vitest + @vue/test-utils + Playwright (frontend)
**Target Platform**: Linux server (Europe ou Afrique de l'Ouest)
**Project Type**: Web application (backend FastAPI + frontend Nuxt 4)
**Performance Goals**: list paginée ≤ 500 ms p95 (200+ indicateurs, 1000+ critères), `/full` ≤ 1 s, `get_facteur` lookup O(log n) via index `(code, pays_iso2, valid_from)`
**Constraints**: aucune route `/admin` exposée aux PME ; RLS catalogue global ; audit append-only ; versioning F04 ; sourcing obligatoire au publish ; DSL profondeur ≤ 6, payload ≤ 8 KB
**Scale/Scope**: 200+ indicateurs, 20+ référentiels, 1000+ critères, 500+ facteurs d'émission ; ~10 endpoints groupés par crud_router ; 3 pages admin frontend (indicateurs, referentiels, facteurs) + sous-pages critères et documents requis

## Constitution Check

Reference: `.specify/memory/constitution.md` v1.0.0.

| # | Principle | Gate question | Status |
|---|-----------|---------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle pointe-t-elle vers une `Source` `verified` ? `source_id NOT NULL` sur lignes critiques (referentiel_indicateur, facteur_emission), `sources[]` ≥ 1 vérifiée pour indicateur/referentiel/critere/document_requis au publish (FR-013). | ✅ |
| P2 | Multi-tenant RLS | Tables catalogue globales (sans `account_id`) — politique RLS alternative `auth.role()='admin' OR (auth.role()='pme' AND status='published')`, comme F08. | ✅ |
| P3 | Audit log append-only | Toute mutation journalisée via décorateur F04 audit (`source_of_change` ∈ {manual, admin}). | ✅ |
| P4 | Versioning + snapshot | `version` + `valid_from`/`valid_to` sur référentiel et facteur_emission ; `version` sur indicateur, critere, document_requis ; snapshot candidatures hors-scope F09. | ✅ |
| P5 | Money typé | Pas de Money direct dans F09 ; éventuels seuils financiers exprimés via Money pegged FCFA-EUR (NFR-005) si Critère porte un seuil monétaire. | ✅ |
| P6 | Pivot Indicateur | OUI — l'objet `Indicateur` EST le pivot ; `referentiel_indicateur` réutilise les mêmes Indicateurs pour multiples référentiels. | ✅ |
| P7 | Plateforme fermée | Aucune route publique non-authentifiée ; routes `/admin/*` restreintes admin ; helpers serveur consommés en interne par F23/F28. | ✅ |
| P8 | Édition manuelle + sync LLM | Tout le contenu catalogue est admin manuel ; aucun pipe LLM dans F09. | ✅ |
| P9 | Tool-use LLM fiable | N/A pour F09 (pas de tool LLM). | ✅ |
| P10 | UX bottom sheet | Toutes les pages admin de F09 utilisent le pattern bottom sheet hérité F06/F08 (NFR-006). | ✅ |

### Contraintes techniques (rappel)

- Stack imposée respectée (FastAPI + Nuxt 4 + Postgres+pgvector).
- Dev local : backend `.venv`, Postgres dockerisé.
- Hébergement Europe/Afrique de l'Ouest.
- Conformité RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010.
- Langue FR par défaut, EN seulement si offre `accepted_languages='en'`.

## Project Structure

### Documentation (this feature)

```text
specs/009-catalog-referentiels-indicateurs/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── indicateurs.openapi.yaml
│   ├── referentiels.openapi.yaml
│   ├── criteres.openapi.yaml
│   ├── documents-requis.openapi.yaml
│   └── facteurs-emission.openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── catalog/
│   │   ├── sources/                # F07 (existing)
│   │   ├── fonds/                  # F08 (existing)
│   │   ├── indicateurs/            # NEW F09
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # registry-driven via crud_router
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── permissions.py
│   │   ├── referentiels/           # NEW F09
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py          # /full + publish validator
│   │   │   ├── validator.py        # weights sum + verified sources + indicateurs published
│   │   │   └── permissions.py
│   │   ├── criteres/               # NEW F09
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── dsl.py              # parser + evaluator (sandbox)
│   │   │   └── permissions.py
│   │   ├── documents_requis/       # NEW F09
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── permissions.py
│   │   └── facteurs_emission/      # NEW F09
│   │       ├── router.py
│   │       ├── schemas.py
│   │       ├── service.py
│   │       ├── lookup.py           # get_facteur(code, pays, at)
│   │       └── permissions.py
│   ├── models/
│   │   ├── indicateur.py           # NEW
│   │   ├── referentiel.py          # NEW
│   │   ├── referentiel_indicateur.py  # NEW
│   │   ├── critere.py              # NEW
│   │   ├── document_requis.py      # NEW
│   │   └── facteur_emission.py     # NEW
│   └── admin/                       # F06 (existing) — registry will be extended
└── alembic/versions/
    └── XXXX_f09_catalog_referentiels_indicateurs.py  # 6 tables + RLS + indexes

frontend/
├── app/
│   ├── pages/
│   │   └── admin/
│   │       └── catalogue/
│   │           ├── indicateurs/
│   │           │   ├── index.vue       # list + filtres pillar/search
│   │           │   └── [id].vue        # detail + edit + publish (bottom sheet)
│   │           ├── referentiels/
│   │           │   ├── index.vue
│   │           │   └── [id].vue        # /full + indicateurs liés + versions (US6)
│   │           ├── criteres/
│   │           │   ├── index.vue
│   │           │   └── [id].vue        # JSON DSL editor (textarea + validation)
│   │           ├── documents-requis/
│   │           │   ├── index.vue
│   │           │   └── [id].vue
│   │           └── facteurs-emission/
│   │               ├── index.vue
│   │               └── [id].vue
│   └── composables/
│       ├── useIndicateurs.ts
│       ├── useReferentiels.ts
│       ├── useCriteres.ts
│       ├── useDocumentsRequis.ts
│       └── useFacteursEmission.ts
└── tests/
    ├── e2e/
    │   ├── indicateurs.crud.spec.ts
    │   ├── referentiels.full.spec.ts
    │   └── facteurs.lookup.spec.ts
    └── unit/
        └── ...

backend/tests/
├── catalog/
│   ├── indicateurs/
│   │   ├── test_crud.py
│   │   ├── test_publish_gate.py
│   │   └── test_versioning.py
│   ├── referentiels/
│   │   ├── test_crud.py
│   │   ├── test_full_endpoint.py
│   │   └── test_publish_validator.py
│   ├── criteres/
│   │   ├── test_dsl_parser.py     # 10 cas (FR-004 / SC-005)
│   │   ├── test_dsl_sandbox.py    # fuzzing négatif
│   │   └── test_owner_filter.py
│   ├── documents_requis/
│   │   └── test_crud.py
│   └── facteurs_emission/
│       ├── test_crud.py
│       ├── test_lookup_helper.py
│       └── test_validity_window.py
└── integration/
    ├── test_rls_catalogue.py
    └── test_audit_versioning_chain.py
```

**Structure Decision**: Web application (backend + frontend) — chaque entité catalogue F09 vit dans `backend/app/catalog/<entity>/` (cohérence avec F07 sources et F08 fonds), modèles SQLAlchemy dans `backend/app/models/`, migration Alembic unique pour les 6 tables (5 entités + table de liaison), et pages admin Nuxt 4 sous `frontend/app/pages/admin/catalogue/<entity>/`. Le `crud_router` F06 absorbe les CRUD via registry (pas de boilerplate par entité). Validator Référentiel et DSL Critère restent isolés en modules dédiés pour testabilité.

## Phase 0 — Research (research.md)

Pas de NEEDS CLARIFICATION résiduel. Recherche limitée à :

1. Confirmer la stratégie RLS catalogue global — politique alternative F08 réutilisable telle quelle.
2. Choix DSL JSON : parser custom récursif Python (≤ 100 lignes) avec whitelist d'opérateurs ; pas de bibliothèque externe (NFR-002).
3. Stratégie versioning facteur_emission : trigger DB sur INSERT pour clore `valid_to` de la version précédente.
4. Index Postgres pour `get_facteur` : `CREATE INDEX ON facteur_emission (code, pays_iso2, valid_from DESC) WHERE valid_to IS NULL OR valid_to > NOW()`.
5. Fenêtre de validation poids : epsilon 0.01 (somme `99.99 ≤ s ≤ 100.01`).

## Phase 1 — Design Artifacts

- **data-model.md** : schéma SQL des 6 tables + contraintes (uniques, FK, CHECK), enums Postgres, RLS policies, index, triggers (clôture `valid_to`).
- **contracts/*.openapi.yaml** : 5 fichiers OpenAPI 3.1 décrivant les CRUD + `publish` + endpoints spécifiques (`/full`, `/criteres?owner_*`, `/documents-requis?owner_*`).
- **quickstart.md** : seed minimal — 3 indicateurs publiés, 1 référentiel publié, 2 critères, 1 document requis, 5 facteurs d'émission.

## Phase 2 — Tasks (tasks.md)

Généré par `/speckit-tasks` à partir de spec + plan + data-model + contracts. Stratégie MVP P1 si > 60 tâches : focaliser US1-US5 (P1) + RLS + DSL + validateur, repousser US6 page visualisation full UI à itération suivante.

## Complexity Tracking

Aucune violation constitutionnelle. Pas d'entrée requise.
