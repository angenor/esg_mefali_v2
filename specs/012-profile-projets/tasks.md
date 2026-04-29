# Tasks: F12 — Profil → Projets

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Format: `- [ ] T### [P?] description`. TDD strict.

## Phase 1 — Migration & RLS
- [ ] T001 `backend/alembic/versions/0012_f12_projets_documents.py`
- [ ] T002 Test `tests/projets/test_migration.py`

## Phase 2 — Storage
- [ ] T010 [P] `app/storage/base.py` (Protocol)
- [ ] T011 [P] `app/storage/local.py`
- [ ] T012 Test `tests/projets/test_storage.py`

## Phase 3 — Schemas & validators
- [ ] T020 [P] `app/projets/schemas.py`
- [ ] T021 [P] `app/projets/validators.py`
- [ ] T022 Test `tests/projets/test_validators.py`

## Phase 4 — Service
- [ ] T030 `app/projets/service.py`
- [ ] T031 `app/projets/events.py`
- [ ] T032 Tests `tests/projets/test_service.py`

## Phase 5 — Documents
- [ ] T040 `app/projets/documents_service.py`
- [ ] T041 Tests `tests/projets/test_documents.py`

## Phase 6 — API
- [ ] T050 `app/api/routes/projets.py`
- [ ] T051 `app/api/routes/projets_documents.py`
- [ ] T052 Wire dans `app/main.py`
- [ ] T053 Tests `tests/projets/test_routes.py`

## Phase 7 — RLS
- [ ] T060 Tests `tests/projets/test_rls.py`

## Phase 8 — Frontend (DEFERRED)
- [ ] T070 [DEFERRED] `frontend/app/pages/profil/projets/index.vue`
- [ ] T071 [DEFERRED] `frontend/app/pages/profil/projets/[id].vue`
- [ ] T072 [DEFERRED] `frontend/app/composables/useProjets.ts`

## Manual tests
Voir `.cc-runtime/logs/manual-tests-12.md`.
