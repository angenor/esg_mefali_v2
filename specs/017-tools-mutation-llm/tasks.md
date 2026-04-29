# Tasks: F17 — Tools de Mutation LLM

**Feature**: F17
**Branch**: `017-tools-mutation-llm`
**Status**: Ready
**Date**: 2026-04-29

## Phase 1 — Decorators & infrastructure (P1)

- [ ] **T001** [P] Create `backend/app/orchestrator/tools/mutations/__init__.py` with `register_mutation_tools()`.
- [ ] **T002** [P] Implement `@destructive` + `MutationConfirmationRequired` in `backend/app/orchestrator/tools/mutations/_destructive.py`.
- [ ] **T003** [P] Implement `@rate_limited(max_per_min=10)` + `RateLimitExceeded` in `backend/app/orchestrator/tools/mutations/_rate_limit.py`.
- [ ] **T004** [P] Test `tests/orchestrator/tools/mutations/test_destructive.py` (NFR-003).
- [ ] **T005** [P] Test `tests/orchestrator/tools/mutations/test_rate_limit.py` (10/min).

## Phase 2 — Tools P1 entreprise/projet (US1, US2)

- [ ] **T006** Tool `update_company_profile` (US1) in `update_company_profile.py` — schema + handler appelle `entreprise.service.update_partial(source_of_change=LLM)`.
- [ ] **T007** Test `test_update_company_profile.py` — happy + audit + extra-field rejection.
- [ ] **T008** Tool `create_project` (US2) in `create_project.py` — schema + handler appelle `projets.service.create_projet`.
- [ ] **T009** Test `test_create_project.py`.
- [ ] **T010** Tool `update_project` (US2) in `update_project.py`.
- [ ] **T011** Test `test_update_project.py`.

## Phase 3 — Tool destructif P1 (US2 delete + US4)

- [ ] **T012** Tool `delete_project` avec `@destructive` in `delete_project.py`.
- [ ] **T013** Test `test_delete_project.py` — confirmed=False rejeté, confirmed=True passe.

## Phase 4 — Garde-fous (US5, SC-003)

- [ ] **T014** Test `test_registry_no_catalog.py` (SC-005).
- [ ] **T015** Test `test_cross_tenant.py` (SC-003).

## Phase 5 — Candidatures CRUD (US3) [DEFERRED si budget tight]

- [ ] **T016** [DEFERRED] Tool `create_candidature`.
- [ ] **T017** [DEFERRED] Tool `update_candidature_status`.
- [ ] **T018** [DEFERRED] Tool `delete_candidature` avec `@destructive`.

## Phase 6 — HTTP route

- [ ] **T019** Endpoint `POST /me/llm-tools/mutations/{name}` in `backend/app/api/routes/llm_mutations.py` avec `get_current_pme`.
- [ ] **T020** Wire router in `backend/app/main.py`.
- [ ] **T021** Integration test `test_route_dispatch.py`.

## Phase 7 — Tools P2 [DEFERRED]

- [ ] **T022** [DEFERRED] `attach_document` (US6 — dépend F22).
- [ ] **T023** [DEFERRED] `recompute_score` (US7 — dépend F23).
- [ ] **T024** [DEFERRED] `generate_attestation` / `revoke_attestation` (US8 — dépend F30).
- [ ] **T025** [DEFERRED] `generate_dossier` (US9 — dépend F26).
- [ ] **T026** [DEFERRED] Endpoint `POST /me/audit-log/{id}/revert` (US10).

## Tests d'acceptation

- SC-001 : tools P1 entreprise + projet CRUD fonctionnent E2E.
- SC-002 : `delete_project` sans confirmation rejeté (T013).
- SC-003 : Cross-tenant → 404 (T015).
- SC-005 : Tool catalogue absent (T014).
- SC-007 : 100% mutations génèrent audit_log (test inclusion).

## Pipeline

- TDD obligatoire pour T004, T005, T007, T009, T011, T013, T014, T015.
- Lint : `ruff check app/orchestrator/tools/mutations/ tests/orchestrator/tools/mutations/`.
- Couverture cible ≥ 80% sur F17 ajouté.

## Scope partial autorisé

Si budget atteint après Phase 4 → livraison MVP minimale (T001-T015) ;
candidatures (T016-T018) + route HTTP (T019-T021) marqués [DEFERRED] sans bloquer le commit.
