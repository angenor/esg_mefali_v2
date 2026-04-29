---
description: "Task list for F04 — Audit Log Append-Only & Versioning"
---

# Tasks: Audit Log Append-Only & Versioning

**Input**: Design documents from `/specs/004-audit-log-versioning/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/*

**Tests**: Tests are REQUIRED for this feature (TDD per project constitution; SC-001..SC-010 are testable acceptance gates).

**Organization**: Grouped by user story (US1..US7). MVP = US1+US2 (audit log core); US4+US5+US6 (versioning + snapshot); US3+US7 are layered after.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different file, no dependency on incomplete tasks.
- **[Story]**: US1..US7. Setup, Foundational, Polish carry no story label.

## Path Conventions

Web app — backend at `backend/`, frontend at `frontend/`. All paths absolute or repo-relative as shown.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Wiring of new module skeletons, no business logic.

- [ ] T001 Create backend module skeleton `backend/app/audit/` with empty `__init__.py`, `helper.py`, `decorator.py`, `blacklist.py`, `schemas.py`, `service.py`
- [ ] T002 [P] Create backend module skeleton `backend/app/versioning/` with empty `__init__.py`, `helpers.py`, `exceptions.py`
- [ ] T003 [P] Create backend module skeleton `backend/app/snapshot/` with empty `__init__.py`, `builder.py`, `schema.py`, `recompute.py`
- [ ] T004 [P] Create backend test directories `backend/tests/unit/audit/`, `backend/tests/unit/versioning/`, `backend/tests/unit/snapshot/`, `backend/tests/integration/`, `backend/tests/perf/`, `backend/tests/e2e/` with `__init__.py` files
- [ ] T005 [P] Add `RUN_PERF` env-gated marker registration to `backend/pyproject.toml` (`[tool.pytest.ini_options].markers = ["perf: opt-in performance tests"]`)
- [ ] T006 [P] Add frontend component test scaffold `frontend/tests/unit/VersionBadge.spec.ts` (empty file, will be filled in Phase 7)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database migration + privilege/RLS plumbing + Pydantic schemas. Every user story depends on these.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T010 Create Alembic migration file `backend/alembic/versions/0004_audit_log_and_versioning.py` (skeleton only — empty `upgrade()` / `downgrade()`)
- [ ] T011 In `0004_audit_log_and_versioning.py`, add `CREATE EXTENSION IF NOT EXISTS btree_gist;` and `CREATE TYPE source_of_change_t AS ENUM ('manual','llm','import','admin','system');` to `upgrade()`; mirror reverse in `downgrade()`
- [ ] T012 In `0004_audit_log_and_versioning.py`, create `audit_log` table per data-model.md §2 (columns + check constraints)
- [ ] T013 [P] In `0004_audit_log_and_versioning.py`, create indexes `audit_log_account_entity_ts_idx`, `audit_log_account_ts_idx`, `audit_log_admin_ts_idx`, `audit_log_request_id_idx`
- [ ] T014 In `0004_audit_log_and_versioning.py`, enable RLS and create policies `audit_log_tenant_isolation`, `audit_log_insert_any`, `audit_log_no_update`, `audit_log_no_delete`
- [ ] T015 In `0004_audit_log_and_versioning.py`, `GRANT INSERT, SELECT ON audit_log TO app_user; REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM app_user, PUBLIC; GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO app_user`
- [ ] T016 [P] In `0004_audit_log_and_versioning.py`, ALTER each of the seven versioned tables (`referentiel`, `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`) to add `version`, `valid_from`, `valid_to`, `parent_id`, `logical_id` (loop over a list of table names)
- [ ] T017 In `0004_audit_log_and_versioning.py`, backfill existing rows: `UPDATE <tbl> SET valid_from=created_at, logical_id=gen_random_uuid() WHERE valid_from IS NULL;` for each versioned table
- [ ] T018 [P] In `0004_audit_log_and_versioning.py`, add `EXCLUDE USING gist` constraint per data-model.md §3 on each of the seven versioned tables
- [ ] T019 [P] In `0004_audit_log_and_versioning.py`, add partial index `<tbl>_logical_active_idx` on `(logical_id) WHERE valid_to IS NULL` for each of the seven tables
- [ ] T020 In `0004_audit_log_and_versioning.py`, ALTER `candidature` ADD COLUMN `snapshot_json JSONB NULL`, `submitted_at TIMESTAMPTZ NULL`
- [ ] T021 In `0004_audit_log_and_versioning.py`, create `candidature_snapshot_guard()` function and `candidature_snapshot_immutable_trg` BEFORE UPDATE trigger per data-model.md §4
- [ ] T022 Apply migration locally: `cd backend && alembic upgrade head`; verify with `psql` that `audit_log` exists and the seven tables now expose the new columns
- [ ] T023 [P] Define Pydantic v2 enum mirror `SourceOfChange` and models `AuditLogEntryIn`, `AuditLogEntryOut` in `backend/app/audit/schemas.py` (`extra='forbid'`)
- [ ] T024 [P] Define `OptimisticLockError(Exception)` in `backend/app/versioning/exceptions.py`
- [ ] T025 [P] Define Pydantic v2 models `Money`, `ReferentielRef`, `OffreRef`, `CritereRef`, `SourceRef`, `SnapshotScores`, `CandidatureSnapshotV1` in `backend/app/snapshot/schema.py` mirroring `contracts/snapshot.schema.json`
- [ ] T026 [P] Add SQLAlchemy ORM model `AuditLog` in `backend/app/models/audit_log.py` mapped to the `audit_log` table
- [ ] T027 [P] Add `VersionedMixin` in `backend/app/models/versioned_mixin.py` (per data-model.md §6) and apply it to the seven existing model classes (one ORM file edit per model: `referentiel.py`, `indicateur.py`, `critere.py`, `formule.py`, `seuil.py`, `facteur_emission.py`, `template.py`)
- [ ] T028 Extend the existing FastAPI request-context middleware (from F02) to expose `request_id` (generate ULID if not provided in `X-Request-Id`) and store it on `request.state.request_id`; also expose `app.current_role` in the DB session via `SET LOCAL app.current_role = ...`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Every business mutation is journaled (P1) — MVP

**Goal**: Deliver `record_audit(...)` helper, the append-only privilege model is enforced, and a sample mutation handler journals exactly one row.

**Independent Test**: As PME of tenant A, `PATCH /entreprises/{id}` updating the `nom` field; assert one new `audit_log` row with the expected attributes; then attempt `UPDATE audit_log` and `DELETE FROM audit_log` from `app_user` and assert privilege denial.

### Tests for User Story 1 (write FIRST, MUST FAIL before implementation)

- [ ] T030 [P] [US1] Unit test `backend/tests/unit/audit/test_helper_basic.py` — calling `record_audit` inserts one row with the supplied fields and a server-side `timestamp`
- [ ] T031 [P] [US1] Unit test `backend/tests/unit/audit/test_helper_noop.py` — `old == new` short-circuits and inserts nothing (FR-019)
- [ ] T032 [P] [US1] Unit test `backend/tests/unit/audit/test_helper_redaction.py` — fuzz blacklisted field names (`password`, `password_hash`, `jwt`, `access_token`, `refresh_token`, `secret`, `api_key`) at depths 1, 2, 3 and assert `[REDACTED]` (FR-013, SC-010)
- [ ] T033 [US1] Integration test `backend/tests/integration/test_audit_privileges.py` — connect as `app_user`, attempt `UPDATE` and `DELETE` on `audit_log`, expect Postgres privilege error (SC-002)
- [ ] T034 [US1] Integration test `backend/tests/integration/test_audit_entreprise_mutation.py` — PATCH `/entreprises/{id}` and assert one matching `audit_log` row (US1 acceptance scenario 1)
- [ ] T035 [US1] Integration test `backend/tests/integration/test_audit_create_event.py` — POST `/projets`, assert audit row with `field=NULL`, `old_value=NULL` (US1 acceptance scenario 3)

### Implementation for User Story 1

- [ ] T040 [US1] Implement field-blacklist redaction `backend/app/audit/blacklist.py` (`AUDIT_REDACTION_FIELDS = (...)`, `redact(value: Any) -> Any` recursive)
- [ ] T041 [US1] Implement `record_audit(...)` in `backend/app/audit/helper.py` — accepts session, entity_type, entity_id, field, old, new, source_of_change, optional notes; pulls `user_id`, `account_id`, `request_id`, `ip` from request context; applies redaction; skips if `old == new`; inserts via SQLAlchemy
- [ ] T042 [US1] Wire `record_audit` invocation into the existing `EntrepriseService.update(...)` (single mutation per call → one audit row)
- [ ] T043 [US1] Wire `record_audit` invocation into the existing `ProjetService.create(...)` and `ProjetService.update(...)`

**Checkpoint**: US1 functional. The audit-log substrate is live; mutations on Entreprise and Projet are journaled.

---

## Phase 4: User Story 2 — Source of every change is traceable (P1)

**Goal**: Provide the `@journal_llm_mutation` decorator and verify the enum is enforced.

**Independent Test**: Decorate a stub LLM tool with `@journal_llm_mutation(entity_type='projet')`; invoke it; assert the resulting audit row has `source_of_change='llm'`. Attempt to insert an unknown enum via raw SQL and assert rejection.

### Tests for User Story 2

- [ ] T050 [P] [US2] Unit test `backend/tests/unit/audit/test_decorator.py` — decorator wraps a coroutine, calls it, then calls `record_audit` with `source_of_change='llm'` and the entity_id returned by the wrapped function
- [ ] T051 [P] [US2] Unit test `backend/tests/unit/audit/test_enum_closed.py` — raw SQL insert with `source_of_change='unknown'` raises `InvalidTextRepresentation`

### Implementation for User Story 2

- [ ] T055 [US2] Implement `@journal_llm_mutation(entity_type)` in `backend/app/audit/decorator.py` — decorator factory, awaits the wrapped tool handler, extracts `entity_id` from the return value (Pydantic model with `.id`), invokes `record_audit` with `source_of_change=SourceOfChange.LLM`
- [ ] T056 [US2] Document the decorator in `backend/app/audit/__init__.py` (re-export) so F17 can import as `from app.audit import journal_llm_mutation`

**Checkpoint**: US1 + US2 fully functional. F17 (later) can adopt the decorator unchanged.

---

## Phase 5: User Story 4 + 5 — Versioning of référentiels and sub-objects (P1)

**Goal**: Deliver `publish_new_version`, `get_active`, the `If-Match` HTTP convention with HTTP 412, and verify the `EXCLUDE` constraint forbids overlap.

**Independent Test**: Publish a new version of a `referentiel` row via the API; verify v_n+1 is open and v_n is closed atomically; then call the publish endpoint with stale `If-Match` and assert HTTP 412. Run a SQL query that tries to insert an overlapping row directly and assert the constraint fires.

### Tests for User Story 4 + 5

- [ ] T060 [P] [US4] Unit test `backend/tests/unit/versioning/test_publish_atomic.py` — `publish_new_version` closes the active row and opens a new one in a single transaction; `parent_id` chain is correct
- [ ] T061 [P] [US4] Unit test `backend/tests/unit/versioning/test_publish_optimistic_lock.py` — stale `version_at_load` raises `OptimisticLockError`
- [ ] T062 [P] [US4] Unit test `backend/tests/unit/versioning/test_get_active.py` — `get_active(at_timestamp=T_in_v2_window)` returns v2; `at_timestamp=T_in_v3_window` returns v3; null when no version active
- [ ] T063 [P] [US5] Integration test `backend/tests/integration/test_versioning_overlap.py` — for each of the 7 tables, attempt direct SQL `INSERT` of an overlapping window, assert `ExclusionViolation` (SC-004)
- [ ] T064 [P] [US5] Integration test `backend/tests/integration/test_versioning_100_publishes.py` — loop 100 successive `publish_new_version` calls, then run the temporal-overlap audit SELECT, assert 0 overlaps (SC-004)
- [ ] T065 [US4] Integration test `backend/tests/integration/test_publish_endpoint_412.py` — POST `/api/v1/referentiels/{logical_id}/publish` with stale `If-Match`, assert 412 + `{"error":"version_conflict","current_version":n}`

### Implementation for User Story 4 + 5

- [ ] T070 [US4] Implement `publish_new_version(session, entity_class, logical_id, new_payload, version_at_load) -> ORMRow` in `backend/app/versioning/helpers.py` — uses `SELECT ... FOR UPDATE`, closes prior, inserts new with incremented version + `parent_id`
- [ ] T071 [US4] Implement `get_active(session, entity_class, logical_id, at_timestamp=None) -> ORMRow | None` in `backend/app/versioning/helpers.py`
- [ ] T072 [US4] Implement FastAPI router `backend/app/api/versioning.py` with `POST /referentiels/{logical_id}/publish` (admin-only), parses `If-Match`, delegates to `publish_new_version`, maps `OptimisticLockError` → 412
- [ ] T073 [P] [US4] Wire the same publish endpoint shape (or a generic factory) for `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template` — one route per table mounted from a small loop
- [ ] T074 [US4] Hook `record_audit(source_of_change=ADMIN)` inside `publish_new_version` so each version-publish event is journaled

**Checkpoint**: Catalogue tables are now versioned; publish flow is live with optimistic lock.

---

## Phase 6: User Story 6 — Candidature snapshot + recompute (P1)

**Goal**: Build `snapshot_json` at submission and expose `POST /candidatures/{id}/recompute-from-snapshot`.

**Independent Test**: Submit a Candidature; assert `snapshot_json` matches the v1 schema and `submitted_at` is set; then change a referential version (out-of-band) and call recompute; assert `recomputed_score == snapshotted_score` to the cent and `drift_detected=false` (SC-003). Attempt to PATCH `snapshot_json` post-submission and assert refusal (SC-008).

### Tests for User Story 6

- [ ] T080 [P] [US6] Unit test `backend/tests/unit/snapshot/test_builder.py` — `build_candidature_snapshot` assembles a v1 dict from a draft Candidature + active référentiel; validates against `contracts/snapshot.schema.json`
- [ ] T081 [P] [US6] Unit test `backend/tests/unit/snapshot/test_builder_missing_referentiel.py` — raises explicit error when `get_active(referentiel)` returns None at submission time (FR-015)
- [ ] T082 [US6] Integration test `backend/tests/integration/test_candidature_submit_snapshot.py` — submit, assert `snapshot_json` populated, `submitted_at` set, valid against JSON Schema
- [ ] T083 [US6] Integration test `backend/tests/integration/test_snapshot_immutable_trigger.py` — direct SQL UPDATE on `snapshot_json` of a submitted row raises trigger exception
- [ ] T084 [US6] Integration test `backend/tests/integration/test_snapshot_immutable_api.py` — PATCH `/candidatures/{id}` attempting to change `snapshot_json` returns 403 and writes an `integrity_violation_attempt` audit row (SC-008)
- [ ] T085 [US6] Integration test `backend/tests/integration/test_recompute_no_drift.py` — recompute right after submission returns `drift_detected=false`, both scores equal (SC-003)
- [ ] T086 [US6] Integration test `backend/tests/integration/test_recompute_with_drift.py` — mock the scoring function to return a different value; assert HTTP 200 with `drift_detected=true` and an audit row of `entity_type=candidature, field=score_drift, source_of_change=system`

### Implementation for User Story 6

- [ ] T090 [US6] Implement `build_candidature_snapshot(session, candidature) -> dict` in `backend/app/snapshot/builder.py` — gathers projet state, offre criteres (id+version), active referentiel (logical_id+version+valid_from), scores from F23 (mocked here), source citations
- [ ] T091 [US6] Modify `CandidatureService.submit(...)` to call `build_candidature_snapshot`, set `snapshot_json` and `submitted_at` atomically inside one transaction; refuse submission if builder raises
- [ ] T092 [US6] Implement `recompute_from_snapshot(snapshot: dict) -> Money` in `backend/app/snapshot/recompute.py` — re-invokes scoring with snapshot data only (no live referential lookup); returns Money tuple
- [ ] T093 [US6] Implement FastAPI handler `POST /candidatures/{id}/recompute-from-snapshot` in `backend/app/api/candidatures_recompute.py` — returns `RecomputeResult` per contract, emits drift audit event when applicable, never returns 4xx on drift
- [ ] T094 [US6] Add API guard in the existing `CandidatureService.update(...)` rejecting any payload that touches `snapshot_json` or `submitted_at` after submission, and journaling the rejected attempt

**Checkpoint**: Submission produces a defensible snapshot; recompute is callable; immutability is enforced at API + DB layers.

---

## Phase 7: User Story 3 + 7 — PME audit-log read view + version badge (P2)

**Goal**: Read endpoint, exports, and the Vue badge component.

**Independent Test**: As PME tenant A with seeded events, call `GET /audit-log?page_size=20` and assert exactly tenant A's rows, ordered DESC, paginated. As admin, call with `?account_id=B` and receive tenant B's rows. Render `<VersionBadge>` in a Vitest test and assert the French string.

### Tests for User Story 3 + 7

- [ ] T100 [P] [US3] Integration test `backend/tests/integration/test_audit_log_endpoint.py` — pagination, ordering, filters (entity_type, entity_id, source_of_change, from/to), `page_size` clamping (FR-017, SC-006)
- [ ] T101 [P] [US3] Integration test `backend/tests/integration/test_audit_log_rls.py` — PME of tenant A querying with forged `?account_id=B` returns zero tenant-B rows (SC-007)
- [ ] T102 [P] [US3] Integration test `backend/tests/integration/test_audit_log_export.py` — CSV and JSON exports respect RLS, contain expected columns
- [ ] T103 [P] [US7] Frontend Vitest `frontend/tests/unit/VersionBadge.spec.ts` — component renders `Évalué selon Référentiel GCF v2 du 15/03/2026` for the sample inputs

### Implementation for User Story 3 + 7

- [ ] T110 [US3] Implement query service `backend/app/audit/service.py` — `list_entries(filters, page, page_size)` returning `AuditLogPage`
- [ ] T111 [US3] Implement FastAPI router `backend/app/api/audit_log.py` — `GET /audit-log`, `GET /audit-log.csv`, `GET /audit-log.json` (RLS active, admin override via `app.current_role`)
- [ ] T112 [P] [US7] Implement `frontend/app/composables/useVersionBadge.ts` — formats date with `Intl.DateTimeFormat('fr-FR', { day:'2-digit', month:'2-digit', year:'numeric' })`
- [ ] T113 [US7] Implement `frontend/app/components/VersionBadge.vue` SFC — props `referentielName: string`, `version: number`, `validFrom: string`; uses `useVersionBadge`

**Checkpoint**: All 7 user stories functional and independently demonstrable.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T120 [P] Performance test `backend/tests/perf/test_audit_throughput.py` (marker `perf`) — sustains ≥100 inserts/sec while 10 reads/sec hold p95 ≤ 200 ms (SC-005)
- [ ] T121 [P] E2E `frontend/tests/e2e/recompute_from_snapshot.spec.ts` (Playwright) — submit candidature, force snapshot mutation attempt via API, assert refusal; recompute and verify badge renders the correct version
- [ ] T122 Refresh `backend/app/middleware/__init__.py` (or equivalent) so `request_id` propagation works from frontend `X-Request-Id` header end-to-end (FR-018)
- [ ] T123 [P] Update `frontend/app/composables/useApi.ts` (or equivalent fetch wrapper) to forward the `X-Request-Id` header on every request
- [ ] T124 [P] Add docstring "use when / don't use when" plus Pydantic schema docs on `record_audit` and `journal_llm_mutation` (constitutional principle P9 prep for F17)
- [ ] T125 Run `specs/004-audit-log-versioning/quickstart.md` end-to-end and tick its validation checklist
- [ ] T126 Verify RLS: connect as `app_user` with `app.current_account_id=A`, run cross-tenant SELECT on `audit_log`, assert empty result set (defensive double-check on top of T101)
- [ ] T127 Run full suite `cd backend && pytest -q && cd ../frontend && pnpm vitest run` and ensure green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependency — can start immediately.
- **Phase 2 (Foundational)**: depends on Phase 1; BLOCKS all user-story phases.
- **Phase 3 (US1)**: starts after Phase 2.
- **Phase 4 (US2)**: starts after Phase 3 (decorator wraps the helper from US1).
- **Phase 5 (US4+US5)**: starts after Phase 2 (independent of US1/US2 except for using `record_audit` in T074).
- **Phase 6 (US6)**: starts after Phase 5 (uses `get_active`, `publish_new_version`).
- **Phase 7 (US3+US7)**: starts after Phase 3 (US3 depends on the helper having produced rows; US7 is fully independent).
- **Phase 8 (Polish)**: depends on all desired stories.

### Within Each User Story

- Tests written and FAILING first (TDD per constitution P3 implications).
- Models/schemas before services.
- Services before endpoints.
- DB migration applied before any test runs.

### Parallel Opportunities

- Phase 1 tasks T002–T006 in parallel.
- Phase 2 tasks T013, T016, T018, T019, T023–T027 marked [P] in parallel (different files / different table loops).
- Within US1: T030, T031, T032 in parallel (different test files).
- Within US4+US5: T060–T064 in parallel.
- Within US6: T080, T081 in parallel.
- Within US3+US7: T100–T103 in parallel.
- US3, US7 and US6 can be worked on concurrently by separate developers once Phase 5 is done.

---

## Parallel Example: User Story 1

```bash
# Tests first (parallel):
Task: "Unit test for record_audit basic insert in backend/tests/unit/audit/test_helper_basic.py"
Task: "Unit test for noop short-circuit in backend/tests/unit/audit/test_helper_noop.py"
Task: "Unit test for redaction blacklist in backend/tests/unit/audit/test_helper_redaction.py"

# Then implementation (sequential within US1):
Task: "Implement blacklist in backend/app/audit/blacklist.py"
Task: "Implement record_audit in backend/app/audit/helper.py"
```

---

## Implementation Strategy

### MVP (US1 + US2)

1. Phase 1 setup, Phase 2 foundational (incl. migration applied).
2. Phase 3 (US1) — append-only journal live.
3. Phase 4 (US2) — LLM decorator ready for F17.
4. STOP, validate, demo.

### Incremental delivery

1. MVP above.
2. Add Phase 5 (US4+US5) — versioning live.
3. Add Phase 6 (US6) — snapshot + recompute live.
4. Add Phase 7 (US3+US7) — read view & badge.
5. Phase 8 — polish, perf, E2E.

### Parallel team strategy

Once Phase 2 done:
- Dev A: US1 → US2.
- Dev B: US4+US5 → US6.
- Dev C: US7 (frontend badge) — fully independent; can start at any time after Phase 1.
- Dev A then picks US3 once US1 is green.

---

## Notes

- [P] = different file, no in-flight dependency.
- Each user story is independently demoable.
- The `EXCLUDE` constraint (T018) is the single most important load-bearing safety net; do not skip its dedicated test (T063).
- Privilege revocation tests (T033) are MANDATORY before any merge — they are the constitutional gate for P3.
- No emojis in source files; this tasks.md uses none in identifiers.
- Commit after each phase or each green test group.
