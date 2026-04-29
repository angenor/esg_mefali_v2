# Implementation Plan: Catalog Sources Management (F07)

**Branch**: `007-catalog-sources-management` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-catalog-sources-management/spec.md`

## Summary

F07 livre la première feature opérationnelle du catalogue : un back-office CRUD complet de l'entité `source` (déjà créée par F03), avec workflow de double vérification, recherche full-text, impact analysis, page publique read-only, et écran d'agrégation des claims non sourcés. Aucune nouvelle table : extension du modèle F03 par index, vues, helpers et endpoints. Réutilisation directe du squelette back-office F06 (registry, etag, crud_router, publish gate, search, stats), de l'audit append-only F04 et du versioning par publication F04, du RLS F02. Les décisions de clarification (double validation stricte, page publique 404 pour `pending`, canonicalisation déterministe d'URL, snapshots immutables, `noindex` MVP) sont intégrées au plan.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5 / Node 22 (frontend).
**Primary Dependencies**: FastAPI, SQLAlchemy 2 + asyncpg, Pydantic v2, Alembic, httpx (HEAD probe), `urllib.parse` + utilitaire local de canonicalisation ; Nuxt 4, Vue 3, Pinia, Tailwind, `@nuxt/ui` ; Voyage AI (déjà intégré F03 pour embeddings) — non requis ici. LLM (minimax-m2.7 via OpenRouter) — non requis ici (F07 est admin pur).
**Storage**: PostgreSQL 16 + pgvector (instance unique, RLS actif). Aucune nouvelle migration de table ; migrations Alembic pour : index GIN tsvector sur `source(title, publisher, notes)`, contrainte unique fonctionnelle `(canonical_url, page)`, vue matérialisée optionnelle pour compteurs d'impact (post-décision : vues SQL simples avec compteurs paramétrés, pas de matview en MVP).
**Testing**: pytest + pytest-asyncio + httpx.AsyncClient (backend) ; Vitest + Vue Test Utils + Playwright (frontend) ; coverage ≥ 80%.
**Target Platform**: Linux server (backend Docker en prod ; venv en dev local), navigateur evergreen (frontend), Postgres 16 (Europe/Afrique de l'Ouest).
**Project Type**: Web application (backend FastAPI + frontend Nuxt 4) — Option 2 du gabarit.
**Performance Goals**: Liste sources < 1s pour 5000 enregistrements (NFR/SC-005) ; endpoint `/impact` < 500ms pour 1000+ objets dépendants (NFR-002/SC-003).
**Constraints**: HEAD HTTP timeout 5s non bloquant (FR-007) ; double validation strictement appliquée serveur (NFR-003) ; RLS Postgres obligatoire ; audit log F04 obligatoire ; versioning F04 sur champs critiques (FR-013).
**Scale/Scope**: 50–100 sources la première semaine, 5000 à terme ; 1–5 admins concurrents ; trafic public marginal en MVP (`noindex`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F07 gère l'entité `source` elle-même (pré-requis du sourçage). Aucune affirmation factuelle nouvelle introduite côté UI ; seule donnée stockée = la source. La double validation stricte (Q1 clarify) garantit que seules les sources vérifiées par 2 admins distincts peuvent référencer/être référencées en `published`. | ✅ |
| P2 | Multi-tenant RLS | La table `source` est globale au catalogue (`account_id` non applicable — sources de référence partagées). Les endpoints admin sont protégés par rôle `Admin`. La page publique `/sources/{id}` est read-only sans auth, ne renvoie aucune donnée tenant. Aucun cross-tenant exposé. | ✅ |
| P3 | Audit log append-only | Chaque mutation (create, update, verify, mark-outdated, delete) inscrit un événement F04 avec `source_of_change='manual'` ou `'admin'`. FR-012 explicite. | ✅ |
| P4 | Versioning + snapshot | FR-013 : modification des champs critiques (`url`, `version`, `publisher`) d'une source `verified` ⇒ nouvelle version F04. Snapshots de candidatures restent immutables (clarify Q4). | ✅ |
| P5 | Money typé | F07 ne manipule aucune valeur monétaire. | ✅ N/A |
| P6 | Pivot Indicateur unique | F07 ne crée pas d'indicateur ; expose seulement les liens d'impact vers les indicateurs existants. | ✅ N/A |
| P7 | Plateforme fermée | Aucun rôle Intermédiaire ajouté. Page publique `/sources/{id}` en `noindex` + pas de sitemap MVP (clarify Q5). | ✅ |
| P8 | Édition manuelle + sync LLM | Les sources sont saisies/modifiées manuellement ; le LLM (post-MVP) pourra proposer des sources via tool dédié, mais l'édition admin reste maître. | ✅ |
| P9 | Tool-use LLM fiable | F07 n'introduit pas de nouveau tool LLM (admin-only). | ✅ N/A |
| P10 | UX bottom sheet | F07 est un module back-office admin (pas de chat) ; UX bottom sheet non applicable, mais aucune dérogation n'est introduite côté chat. | ✅ N/A |

### Contraintes techniques (rappel)

- Stack imposée respectée (Nuxt 4 + FastAPI + Postgres+pgvector + Voyage + minimax-m2.7 OpenRouter — ces deux derniers non requis par F07).
- Dev local : backend `.venv`, Postgres unique service Docker, frontend `pnpm dev`.
- Hébergement Europe/Afrique de l'Ouest uniquement (rappel infra ; F07 n'introduit aucune dépendance USA).
- Conformité RGPD/2013-450/UEMOA : aucune donnée personnelle PME manipulée par F07 ; les champs `captured_by`/`verified_by` sont des UUID admin internes.
- Langue par défaut français (UI admin) ; interface anglaise hors scope F07.

## Project Structure

### Documentation (this feature)

```text
specs/007-catalog-sources-management/
├── plan.md                # Ce fichier
├── research.md            # Phase 0 (ci-dessous)
├── data-model.md          # Phase 1
├── quickstart.md          # Phase 1
├── contracts/             # Phase 1 (OpenAPI + types)
│   ├── admin-sources.openapi.yaml
│   └── public-sources.openapi.yaml
├── checklists/
│   └── requirements.md    # Issu de speckit-specify
└── tasks.md               # Phase 2 (speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/
│   └── versions/
│       └── 007_xxx_sources_indices_canonical.py    # GIN tsvector + unique (canonical_url, page)
├── app/
│   ├── catalog/
│   │   └── sources/
│   │       ├── __init__.py
│   │       ├── canonicalize.py        # Utilitaire URL canonique (déterministe)
│   │       ├── http_probe.py          # HEAD probe asynchrone, timeout 5s
│   │       ├── repository.py          # Accès SQLAlchemy (list, get, create, update, soft-delete)
│   │       ├── service.py             # Logique métier (verify, mark-outdated, impact)
│   │       ├── impact.py              # Agrégation des FK depuis indicateurs/criteres/...
│   │       ├── schemas.py             # Pydantic v2 DTO (create/read/update/list/impact)
│   │       ├── permissions.py         # Rôle Admin + double-validation guard
│   │       ├── search.py              # Wrapper full-text (tsvector + accents)
│   │       └── router.py              # FastAPI router /admin/sources et /admin/unsourced-claims
│   ├── api/
│   │   └── public_sources.py          # Router public /sources/{id} (noindex)
│   └── tests/
│       └── catalog/sources/
│           ├── unit/
│           │   ├── test_canonicalize.py
│           │   ├── test_http_probe.py
│           │   └── test_permissions.py
│           ├── integration/
│           │   ├── test_crud.py
│           │   ├── test_verify_workflow.py
│           │   ├── test_mark_outdated.py
│           │   ├── test_impact.py
│           │   ├── test_search.py
│           │   └── test_public_page.py
│           └── contract/
│               └── test_openapi_admin.py

frontend/
├── app/
│   ├── pages/
│   │   ├── admin/
│   │   │   ├── sources/
│   │   │   │   ├── index.vue              # Liste paginée + filtres + recherche
│   │   │   │   ├── new.vue                # Formulaire création
│   │   │   │   └── [id]/
│   │   │   │       ├── index.vue          # Détail / édition
│   │   │   │       ├── verify.vue         # Action verify
│   │   │   │       └── impact.vue         # Vue impact
│   │   │   └── unsourced-claims.vue       # US6
│   │   └── sources/
│   │       └── [id].vue                   # Page publique noindex
│   ├── composables/
│   │   ├── useAdminSources.ts
│   │   └── usePublicSource.ts
│   ├── components/
│   │   └── admin/sources/
│   │       ├── SourceForm.vue
│   │       ├── SourceTable.vue
│   │       ├── SourceFilters.vue
│   │       ├── SourceImpactPanel.vue
│   │       └── DuplicateBanner.vue
│   └── stores/
│       └── adminSources.ts
└── tests/
    ├── unit/
    │   └── components/admin/sources/*.test.ts
    └── e2e/
        └── admin-sources.spec.ts          # Playwright : create + verify + impact + outdated
```

**Structure Decision**: Option 2 (Web application), aligné avec la layout existante (`backend/app/...`, `frontend/app/...`). F07 ajoute un sous-module `catalog/sources/` côté backend et des routes `admin/sources` + `sources/[id]` côté frontend, sans réorganiser l'arborescence existante livrée par F01–F06.

## Phase 0 — Research (résumé, détail dans `research.md`)

Décisions techniques notables :

- **Canonicalisation URL** : utilitaire pur Python (pas de dépendance externe lourde) ; module `canonicalize.py`. Tests d'idempotence + table de cas de référence (FR-011).
- **HEAD probe** : `httpx.AsyncClient` avec `timeout=5.0`, `follow_redirects=True`, `verify=True` ; non bloquant — le warning est retourné dans la réponse de création comme champ `head_warning`.
- **Recherche full-text** : colonne générée `tsvector` (Postgres `unaccent` + `french`) sur `coalesce(title,'')||' '||coalesce(publisher,'')||' '||coalesce(notes,'')` ; index GIN. Tri pertinence via `ts_rank_cd`.
- **Impact analysis** : agrégation par `COUNT(*) FILTER` sur les FK existantes (indicateur, critère, formule, facteur d'émission, document_requis, référentiel, skill, candidature) en une requête CTE. Pagination par catégorie (lazy expansion via `?expand=criteres&page=2`). Pas de matview en MVP.
- **Versioning** : delta des champs critiques détecté en service ; appel au helper F04 `version_publish.bump_source_version(source_id, by=user_id)` ; sinon update inline.
- **Audit** : helper F04 `audit.record(entity='source', entity_id, action, actor, before, after, source_of_change='admin')` appelé sur toutes les mutations.
- **Page publique** : route Nuxt SSR `/sources/[id]`, fetch via API publique restreinte aux statuts `verified|outdated`, header `X-Robots-Tag: noindex` + `<meta name="robots" content="noindex">`. Aucune donnée tenant exposée.
- **Permissions** : guard `assert_admin` (F02) + check serveur `verified_by != captured_by` dans le service `verify`. Aucun bypass via env ou flag.

## Phase 1 — Design Artifacts (résumé, fichiers générés)

- `data-model.md` : description précise de la table `source` (référence F03), colonnes ajoutées par migration (colonne générée `search_vector`, contrainte unique `(canonical_url, page)`), index GIN, et schéma de `impact_response`.
- `contracts/admin-sources.openapi.yaml` : endpoints `/admin/sources` (GET list, POST create, GET id, PATCH id, DELETE id, POST id/verify, POST id/mark-outdated, GET id/impact) + `/admin/unsourced-claims`.
- `contracts/public-sources.openapi.yaml` : endpoint `GET /sources/{id}` public (verified|outdated only, noindex header).
- `quickstart.md` : pas-à-pas dev (migration, seed 3 sources, lancement back+front, scénario de test E2E manuel).

## Complexity Tracking

Aucune dérogation. Aucune ligne à remplir.
