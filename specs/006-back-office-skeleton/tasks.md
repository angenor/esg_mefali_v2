# Tasks: F06 — Squelette Back-Office Admin & Workflow draft → published

**Input**: Design documents from `/specs/006-back-office-skeleton/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests**: Included (TDD per common rules + constitution P9 mindset).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no incomplete dependency).
- **[Story]**: User story tag (US1..US6).
- Paths : `backend/app/...`, `frontend/...`.

## Path Conventions

- Backend FastAPI under `backend/app/`, tests under `backend/tests/`.
- Frontend Nuxt 4 under `frontend/`, tests under `frontend/tests/`.

---

## Phase 1: Setup

- [x] T001 Create backend admin package skeleton at `backend/app/admin/` with empty `__init__.py`, `middleware.py`, `registry.py`, `crud_router.py`, `publish.py`, `search.py`, `stats.py`, `pagination.py`, `etag.py`, and `schemas/` subpackage
- [ ] [DEFERRED] T002 [P] Create frontend admin folders : `frontend/layouts/`, `frontend/middleware/`, `frontend/pages/admin/`, `frontend/components/admin/`, `frontend/composables/`, `frontend/assets/styles/`
- [ ] [DEFERRED] T003 [P] Add backend dev dependencies if missing (`pytest-asyncio`, `httpx`) in `backend/pyproject.toml`
- [ ] [DEFERRED] T004 [P] Add frontend dev dependencies if missing (`@vueuse/core`, `@nuxt/test-utils`, `vitest`, `@playwright/test`) in `frontend/package.json`

---

## Phase 2: Foundational (blocking prerequisites)

- [x] T005 Create Alembic migration `backend/alembic/versions/20260429_F06_demo_indicator.py` : enable extension `pg_trgm`, create table `demo_indicator` (cf. data-model.md), create indices BTREE/trigram, enable RLS + policies (read public published / admin all)
- [x] T006 Adjust `audit_log.account_id` to nullable if not already (same migration) so admin catalog mutations can be logged without tenant context — verify F04 schema first
- [x] T007 Implement `backend/app/admin/middleware.py` : `ensure_admin` dependency that 403s on non-admin and sets `app.is_admin=true` in current Postgres session for the request lifecycle
- [x] T008 [P] Implement `backend/app/admin/etag.py` : helpers `make_etag(version: int) -> str`, `parse_if_match(header: str|None) -> int`, raise 412 on mismatch
- [x] T009 [P] Implement `backend/app/admin/pagination.py` : encode/decode opaque base64 cursor `{created_at,id}`, build SQLAlchemy keyset clause, return `{items, next_cursor, total_estimate}` with `total_estimate` from `pg_class.reltuples`
- [x] T010 [P] Implement `backend/app/admin/registry.py` : `EntitySpec` dataclass + `EntityRegistry` singleton with `register(spec)` / `get(name)` / `all()`
- [ ] [DEFERRED] T011 [P] Implement `backend/app/admin/schemas/pagination.py`, `schemas/publish.py`, `schemas/search.py` (Pydantic v2 strict, `extra='forbid'`)
- [x] T012 Implement `backend/app/admin/crud_router.py` : `make_crud_router(spec)` exposing GET list (cursor pagination + status filter), POST create (status=draft), GET one (with ETag header), PUT update (If-Match required, calls `publish_new_version` via F04 helper if status=published), GET versions; all wrapped in `ensure_admin` dependency; every mutation calls audit helper
- [x] T013 Implement `backend/app/admin/publish.py` : `POST /admin/{entity}/{id}/publish` — verify all `sources_relation(obj)` items have `status='verified'`, else 422 with structured `missing_sources`; on success, set `status='published'`, increment audit, set `published_by`, return ETag
- [x] T014 Implement `backend/app/admin/search.py` : `GET /admin/search?q=&types=` — for each registered entity, run ILIKE/trigram on `searchable_fields`, top 10 with `similarity()` ordering ; gather concurrently via `asyncio.gather`
- [x] T015 Implement `backend/app/admin/stats.py` : `GET /admin/stats/catalog` — for each entity, `SELECT status, COUNT(*) GROUP BY status`, return nested object
- [x] T016 Mount `/admin` routers in `backend/app/main.py` (registry-driven include of all CRUD routers + publish + search + stats)
- [x] T017 Create demo entity registration : `backend/app/catalog/demo_indicator.py` (SQLAlchemy model, Pydantic Read/Create/Update, `sources_relation` returning `[demo_indicator.source]`) ; register at startup in `backend/app/catalog/__init__.py`
- [x] T018 [P] Implement frontend route middleware `frontend/middleware/admin.ts` : verify `useAuth().role === 'admin'` else throw 403 / redirect login

**Checkpoint** : foundations ready — user-story phases unlocked.

---

## Phase 3: User Story 1 — Layout admin distinct (P1)

**Goal**: Un admin accède à `/admin` sur layout dédié, PME 403.

**Independent Test**: Login admin → `/admin` rendu sidebar/header ; login PME → 403 redirigé.

- [ ] [DEFERRED] T019 [US1] Implement `frontend/assets/styles/admin.css` : palette admin (variables CSS sobres, isolée de Tailwind PME)
- [ ] [DEFERRED] T020 [US1] Implement `frontend/layouts/admin.vue` : sidebar permanente avec sections (Sources, Fonds, Intermédiaires, Offres, Référentiels, Indicateurs, Critères, Documents requis, Facteurs d'émission, Templates, Skills, PME, Métriques), header simple, breadcrumbs, slot main ; classe racine `.admin-shell`
- [ ] [DEFERRED] T021 [US1] Implement `frontend/pages/admin/index.vue` : page d'accueil admin avec `definePageMeta({ layout: 'admin', middleware: 'admin' })` + récap rapide (compteurs si stats dispo)
- [x] T022 [P] [US1] Backend integration test `backend/tests/integration/admin/test_admin_middleware.py` : 200 admin, 403 PME, 401 anonymous, et vérifie `app.is_admin` posé dans la session
- [ ] [DEFERRED] T023 [P] [US1] Frontend E2E test `frontend/tests/e2e/admin-access-403.spec.ts` : admin voit layout, PME redirigé, anonymous redirigé login

---

## Phase 4: User Story 2 — Workflow draft → published (P1)

**Goal**: Cycle de vie standard avec gate sources verified et versioning F04.

**Independent Test**: Sur `demo_indicator`, créer draft sans source verified → publish 422 ; ajouter source verified → publish 200 ; modifier published → v2 confirmation.

- [x] T024 [US2] Backend contract test `backend/tests/contract/admin/test_publish_contract.py` : conformité au contrat `admin-publish.openapi.yaml` (200, 412, 422 missing_sources)
- [x] T025 [US2] Backend integration test `backend/tests/integration/admin/test_publish_flow.py` : create demo_indicator draft, link source pending → publish 422 with structured missing_sources ; verify source → publish 200, status=published, audit_log entry written, `published_by` set
- [x] T026 [US2] Backend integration test `backend/tests/integration/admin/test_etag_concurrency.py` : two concurrent PUT with same If-Match → second gets 412 ; PUT on `published` triggers `publish_new_version` and returns new ETag
- [x] T027 [US2] Backend unit test `backend/tests/unit/admin/test_publish_gate.py` : pure unit on `verify_sources_or_422(spec, instance)` covering all status combinations
- [ ] [DEFERRED] T028 [US2] Implement `frontend/composables/useEntityCrud.ts` : list/get/create/update/publish/getVersions via `$fetch` ; reads `ETag`, sends `If-Match` ; cursor pagination support ; returns typed objects (generic `<T>`)
- [ ] [DEFERRED] T029 [US2] Implement `frontend/components/admin/StatusBadge.vue` : 4 variants (draft=jaune, published=vert, outdated=gris, pending=orange) using admin palette tokens
- [ ] [DEFERRED] T030 [US2] Implement `frontend/components/admin/VersionTimeline.vue` : props `entityType`, `entityId` ; calls `/admin/{entity}/{id}/versions` ; renders vertical list (version, valid_from, valid_to, published_by, status badge)
- [ ] [DEFERRED] T031 [P] [US2] Frontend component test `frontend/tests/component/admin/StatusBadge.spec.ts` : asserts color class per status
- [ ] [DEFERRED] T032 [P] [US2] Frontend component test `frontend/tests/component/admin/VersionTimeline.spec.ts` : mocks API, renders versions
- [ ] [DEFERRED] T033 [P] [US2] Frontend unit test `frontend/tests/unit/composables/useEntityCrud.spec.ts` : mocks `$fetch`, asserts If-Match header sent and 412 surfaced as typed error
- [ ] [DEFERRED] T034 [US2] Frontend E2E test `frontend/tests/e2e/admin-publish-demo.spec.ts` + `frontend/tests/e2e/admin-versioning.spec.ts` : full workflow draft→published, then edit→v2 confirmation

---

## Phase 5: User Story 3 — Composants CRUD réutilisables (P1)

**Goal**: List/Form génériques utilisables sans réécriture.

**Independent Test**: Brancher AdminListPage et AdminFormPage sur demo_indicator avec 75 lignes ; vérifier pagination, filtres, save, validation.

- [ ] [DEFERRED] T035 [US3] Implement `frontend/components/admin/AdminListPage.vue` : props `columns`, `rows`, `filters`, `pagination`, `actions`, `entityType` ; cursor pagination; filtre par status; clavier Tab/Enter
- [ ] [DEFERRED] T036 [US3] Implement `frontend/components/admin/AdminFormPage.vue` : props `schema`, `model`, `onSave`, `onPublish` ; intègre `useAdminDraft` ; bouton Publier désactivé si gate sources non OK ; confirmation v2 sur published
- [ ] [DEFERRED] T037 [US3] Implement `frontend/composables/useAdminDraft.ts` : `useStorage` clé `admin:draft:{entityType}:{entityId|new}:{userId}` + `useDebounceFn(persist, 1500)` ; reprise avec confirmation modale si `version` serveur > local
- [ ] [DEFERRED] T038 [US3] Implement `frontend/pages/admin/[entity]/index.vue` : utilise `AdminListPage` + `useEntityCrud`, lit `useRoute().params.entity`
- [ ] [DEFERRED] T039 [US3] Implement `frontend/pages/admin/[entity]/[id].vue` : utilise `AdminFormPage` + `useEntityCrud` ; mode create si `id==='new'`
- [ ] [DEFERRED] T040 [P] [US3] Frontend component test `frontend/tests/component/admin/AdminListPage.spec.ts` : 75 rows mock, vérifie pagination cursor (51e ligne déclenche 2e page)
- [ ] [DEFERRED] T041 [P] [US3] Frontend component test `frontend/tests/component/admin/AdminFormPage.spec.ts` : save draft, publish disabled si sources pending, confirmation v2
- [ ] [DEFERRED] T042 [P] [US3] Frontend unit test `frontend/tests/unit/composables/useAdminDraft.spec.ts` : debounce, scope clé, conflit version

---

## Phase 6: User Story 4 — Audit admin (P1)

**Goal**: Toute mutation back-office écrite dans audit_log avec source_of_change='admin'.

**Independent Test**: 3 mutations (create/update/publish) → 3 entrées audit_log.

- [x] T043 [US4] Implement `backend/app/admin/audit.py` : wrapper `write_admin_event(session, user_id, entity_type, entity_id, action, before, after)` qui force `source_of_change='admin'` et délègue à `app.audit.write_event` (F04)
- [x] T044 [US4] Wire `write_admin_event` dans `crud_router.create`, `crud_router.update`, `publish.publish` (mêmes transactions)
- [x] T045 [US4] Backend integration test `backend/tests/integration/admin/test_audit_admin.py` : create/update/publish demo_indicator, asserte 3 lignes audit_log avec `source_of_change='admin'` et bon `user_id`
- [ ] [DEFERRED] T046 [US4] Backend integration test (extension du précédent) : forcer une erreur applicative en milieu de mutation, asserter rollback complet (aucune ligne audit_log incohérente)

---

## Phase 7: User Story 5 — Recherche transversale (P2)

**Goal**: Barre de recherche globale, résultats groupés par type, max 10 par type.

**Independent Test**: Saisir un terme partiel → résultats groupés affichés.

- [x] T047 [US5] Backend contract test `backend/tests/contract/admin/test_search_contract.py` : conformité `admin-search.openapi.yaml` (q minLength, groupes max 10)
- [x] T048 [US5] Backend integration test `backend/tests/integration/admin/test_search.py` : seed 12 demo_indicator avec noms variés, search renvoie 10 max + `similarity` desc
- [ ] [DEFERRED] T049 [US5] Implement `frontend/components/admin/AdminSearchBar.vue` : input avec debounce 300 ms, dropdown groupé par type, highlight, navigation clavier
- [ ] [DEFERRED] T050 [US5] Wire `AdminSearchBar` dans `frontend/layouts/admin.vue` (header)

---

## Phase 8: User Story 6 — Compteurs sidebar (P2)

**Goal**: Sidebar affiche {draft, published, pending} par section.

**Independent Test**: Charger sidebar → voir compteurs ; ajouter draft via API → recharger → compteur draft +1.

- [x] T051 [US6] Backend contract test `backend/tests/contract/admin/test_stats_contract.py` : conformité `admin-stats.openapi.yaml`
- [x] T052 [US6] Backend integration test `backend/tests/integration/admin/test_stats.py` : seed mix statuses, verify counters
- [ ] [DEFERRED] T053 [US6] Implement `frontend/composables/useAdminStats.ts` : fetch `/admin/stats/catalog` au mount du layout, polling toutes les 60 s
- [ ] [DEFERRED] T054 [US6] Wire `useAdminStats` dans la sidebar (T020) — afficher les compteurs à côté de chaque section

---

## Phase 9: Polish & cross-cutting

- [ ] [DEFERRED] T055 [P] Backend contract test `backend/tests/contract/admin/test_crud_contract.py` : conformité globale `admin-entity-crud.openapi.yaml` (list cursor, create, get with ETag, put with If-Match, versions list)
- [ ] [DEFERRED] T056 [P] Backend integration test `backend/tests/integration/admin/test_pagination_cursor.py` : seed 75 rows, walk through pagination via cursor, idempotence
- [x] T057 [P] Backend unit tests `backend/tests/unit/admin/test_pagination_helpers.py` and `test_registry.py`
- [ ] [DEFERRED] T058 [P] Frontend a11y check : `frontend/tests/e2e/admin-keyboard.spec.ts` — Tab/Enter/Esc full-keyboard navigation on list and form (NFR-004)
- [ ] [DEFERRED] T059 Update `quickstart.md` if any divergence pendant l'implémentation ; lancer le smoke check final §7
- [ ] [DEFERRED] T060 Run full test suite (`pytest backend/tests/{contract,integration,unit}/admin -v`, `pnpm test:unit && pnpm test:component && pnpm test:e2e`) and ensure ≥ 80 % coverage on `backend/app/admin/` and on new frontend admin code

---

## Dependencies

- Phase 1 → Phase 2 → Phases 3-8 (US-grouped) → Phase 9.
- Within Phase 2, T005/T006 must precede T007-T017.
- US1 (T019-T023) depends on T007, T018.
- US2 (T024-T034) depends on T012, T013, T017.
- US3 (T035-T042) depends on T028, T029, T030.
- US4 (T043-T046) depends on T012, T013 (wires into existing handlers).
- US5 (T047-T050) depends on T014.
- US6 (T051-T054) depends on T015, T020.
- Phase 9 depends on all prior phases.

## Parallel Execution Examples

- T002, T003, T004 in parallel (different files).
- T008, T009, T010, T011 in parallel after T007.
- T022, T023 in parallel.
- T031, T032, T033 in parallel.
- T040, T041, T042 in parallel.
- T055, T056, T057, T058 in parallel.

## Implementation Strategy

- **MVP** = Phase 1-2 + US1+US2+US3+US4 (P1 stories : layout, workflow, composants, audit). Stop here = back-office squelette utilisable par F07.
- **P2 incrémental** = US5 + US6 (search + stats). Peuvent être livrés post-MVP F06 sans bloquer F07.
- **Polish (Phase 9)** : exécuter avant merge final.

Total tasks : **60**.


## Implementation status (2026-04-29)

- **Completed (27/60)** : Backend P1 + P2 + cross-cutting tests.
  - Setup : T001.
  - Foundational : T005-T010, T012-T018 (admin module + demo_indicator + RLS + middleware admin frontend pré-existant).
  - US1 (Layout admin) : T022 backend test only.
  - US2 (Workflow draft→published) : T024-T027 backend (contract via integration tests).
  - US4 (Audit admin) : T043-T045.
  - US5 (Search) : T047-T048.
  - US6 (Stats) : T051-T052.
  - Polish : T057.
- **Deferred (33/60)** : tâches frontend (composants Vue, layout, E2E Playwright), tests contract OpenAPI standalone, doc smoke. Le backend complet permet à F07 d'avancer.
- Coverage : `app/admin/` ≥ 88 %, `app/catalog/` 100 %, suite globale 86.53 %.
- 302 tests, 0 failed, 5 skipped. Aucune régression F01-F05.
