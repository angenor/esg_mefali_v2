# F04 — Manual Test Log

Date: 2026-04-29
Branch: 004-audit-log-versioning
Migration: 0004_audit_log_and_versioning

## Automated coverage summary

- Total backend tests: **244 passed, 1 skipped**
- Backend coverage: **85.08%** (gate: 80%)
- Frontend tests: **8 passed** (vitest), incl. 3 VersionBadge specs
- Ruff lint: clean (0 errors)
- F01-F03 regression: green (no regression introduced)

## SC gates verified by automated tests

| SC ID | Gate | Test | Status |
|-------|------|------|--------|
| SC-002 | Append-only privilege | `tests/integration/test_audit_privileges.py` (UPDATE/DELETE/TRUNCATE rejected for `app_user`) | PASS |
| SC-003 | Recompute no drift | `tests/unit/snapshot/test_recompute.py::test_no_drift_when_default_provider` | PASS |
| SC-004 | EXCLUDE no overlap | `tests/integration/test_versioning_overlap.py` (4 tables × overlap insertion) + `test_chain_of_publishes_no_overlap` | PASS |
| SC-006 | Page size clamp | `tests/integration/test_audit_service.py::test_list_entries_pagination_and_filters` | PASS |
| SC-008 | Snapshot immutable | `tests/integration/test_snapshot_immutable.py::test_snapshot_immutable_trigger_blocks_update` | PASS |
| SC-010 | Redaction blacklist | `tests/unit/audit/test_blacklist.py` + `test_record_audit_redacts_blacklisted_field` | PASS |

Per-component fine-grained gates:

- T030 record_audit insert one row → green
- T031 record_audit no-op when old==new → green
- T035 create event with field=NULL → green
- T050 @journal_llm_mutation async/sync paths → green
- T051 enum closed list rejects unknown SQL value → green
- T060 publish_new_version atomic close + open → green
- T061 OptimisticLockError on stale version_at_load → green
- T062 get_active returns correct row at timestamp → green
- T063 EXCLUDE constraint per table → green (4 existing tables)
- T064 (light) chain of 5 publishes → 0 overlaps → green
- T080 build_candidature_snapshot Pydantic v1 round-trip → green
- T083 candidature snapshot immutable trigger → green
- T085 recompute no-drift happy path → green
- T086 drift detection with mock provider → green
- T100 list_entries pagination + filters + clamp → green
- T103 VersionBadge French formatting → green

## Manual checks performed

1. **Migration applies cleanly**: `alembic upgrade head` ✓ ; `alembic downgrade -1` ✓ ; `alembic upgrade head` ✓ (idempotent).
2. **audit_log columns**: `\d audit_log` shows `request_id text`, `ip inet`, `source_of_change source_of_change_t` (ENUM), 4 new composite indexes, RLS forced + policies attached.
3. **Versioned tables**: `\d indicateur` shows `valid_from timestamptz NOT NULL DEFAULT now()`, `valid_to timestamptz`, `parent_id uuid`, `logical_id uuid NOT NULL DEFAULT gen_random_uuid()`, `version int NOT NULL DEFAULT 1`, plus `EXCLUDE USING gist` constraint and partial active index. Same for `critere`, `facteur_emission`, `template`, `referentiel` (latter with `version_num` integer alongside legacy `version` TEXT).
4. **app_user privilege gate**: Connecting via the `app_user` role and running `UPDATE audit_log SET …` returns `permission denied for table audit_log` (Postgres).
5. **Snapshot trigger**: Direct UPDATE on `snapshot_json` after `submitted_at` is set raises `snapshot_json is immutable after submission (candidature.id=…)` ; pre-submission UPDATE succeeds.
6. **EXCLUDE constraint**: Direct INSERT of overlapping `[valid_from, valid_to)` for the same `logical_id` is rejected with `conflicting key value violates exclusion constraint`.
7. **Optimistic-lock 412 path**: `publish_new_version(..., version_at_load=99)` raises `OptimisticLockError`. The `/api/v1/{table}/{logical_id}/publish` route maps it to HTTP 412 with `{"error":"version_conflict","current_version":<n>}`.

## Deferred / out-of-scope for F04

- T120 perf test (≥100 inserts/sec, p95 ≤ 200 ms) — `pytest -m perf` opt-in marker registered, harness left as a TODO since F04 doesn't bring its own load fixtures (better suited once F23 scoring is real).
- T121 Playwright E2E flow — test scaffold only, real journey wired in F22/F23.
- T101 cross-tenant RLS endpoint test — covered indirectly via the existing F02 `_rls_check` and the `audit_log_tenant_isolation` policy declared in 0004 ; full PME-vs-PME scenario will land with F11 (multi-tenant fixtures).

## Files touched

- backend/alembic/versions/0004_audit_log_and_versioning.py (new)
- backend/app/audit/{__init__,blacklist,decorator,helper,schemas,service}.py (new)
- backend/app/versioning/{__init__,exceptions,helpers}.py (new)
- backend/app/snapshot/{__init__,builder,recompute,schema}.py (new)
- backend/app/middleware/request_id.py (new)
- backend/app/api/routes/{audit_log,candidatures,versioning}.py (new)
- backend/app/main.py (router + middleware wiring)
- backend/tests/unit/audit/{test_blacklist,test_decorator,test_schemas}.py (new)
- backend/tests/unit/snapshot/{test_recompute,test_schema}.py (new)
- backend/tests/integration/{test_audit_helper,test_audit_privileges,test_audit_service,test_recompute_no_drift,test_snapshot_immutable,test_versioning_overlap,test_versioning_publish}.py (new)
- frontend/app/composables/useVersionBadge.ts (new)
- frontend/app/components/VersionBadge.vue (new)
- frontend/tests/unit/VersionBadge.spec.ts (new)
