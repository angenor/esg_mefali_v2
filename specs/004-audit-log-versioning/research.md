# Research — F04 Audit Log Append-Only & Versioning

**Feature**: 004-audit-log-versioning
**Date**: 2026-04-29
**Status**: Phase 0 complete — all unknowns resolved.

## R1. Append-only enforcement strategy

**Decision**: Postgres-level GRANT/REVOKE on the `audit_log` table — `app_user` receives `INSERT` only; `migrator` retains all DDL; `UPDATE`, `DELETE`, `TRUNCATE` are explicitly revoked from `app_user` and from `PUBLIC`. A defensive RLS policy `FOR UPDATE USING (false)` and `FOR DELETE USING (false)` is added as a belt-and-braces measure in case a future migration accidentally re-grants the privilege.

**Rationale**: Privilege revocation is the only mechanism Postgres enforces unconditionally regardless of the application code path. It satisfies SC-002 deterministically. RLS-only would be insufficient because a future bug or admin override could disable it.

**Alternatives considered**:
- DB triggers blocking UPDATE/DELETE — rejected: triggers can be disabled by a superuser, less robust than privilege revocation, and add per-row overhead.
- Application-layer guard only — rejected: a single forgotten path or raw SQL session breaks the invariant; constitution P3 requires DB-enforced append-only.

## R2. Where to apply the audit helper

**Decision**: An explicit Python helper `record_audit(...)` invoked from each service-layer mutation method. No DB triggers in MVP. A Python decorator `@journal_llm_mutation(entity_type=...)` wraps LLM tool handlers (consumed by F17) so the LLM path uses the same helper and sets `source_of_change='llm'` automatically.

**Rationale**: Triggers cannot reliably attribute the `source_of_change` (the DB does not know whether the calling SQL came from a manual API handler or an LLM tool). Service-layer invocation also keeps the redaction blacklist in Python where it can be unit-tested.

**Alternatives considered**:
- DB triggers + a session GUC `app.source_of_change` — rejected as opaque and brittle (forgetting to set the GUC silently mis-attributes events).
- ORM event listeners only — rejected because raw-SQL paths bypass them.

## R3. `source_of_change` enum values

**Decision**: Postgres ENUM `source_of_change_t` with values `manual`, `llm`, `import`, `admin`, `system`. Constitution P3 lists the first four as the closed set; the F04 spec adds `system` for migrations and background jobs without a user. This is treated as an EXPANSION of the constitutional set, not a redefinition: every mutation type listed in P3 still has a dedicated value, and `system` is reserved for non-attributable platform actions (data migrations, scheduled cleanups). The enum is closed at the DB level — no free-form value is permitted.

**Rationale**: Migrations and the temporal-overlap sanity job need a non-null `source_of_change`. Forcing them to claim `admin` would lie about provenance and damage audit defensibility. The expansion is purely additive and does not weaken any P3 rule.

**Alternatives considered**:
- Map system events to `admin` — rejected: false attribution.
- Allow `NULL` — rejected: P3 requires the field to be non-null.

## R4. Versioned tables — logical identity

**Decision**: Each versioned table receives a non-null `logical_id UUID` column generated at the first version (default `gen_random_uuid()`) and copied unchanged to every subsequent version. Row PK `id` remains the per-version unique key. `parent_id` (nullable, FK to `id` of same table) records the ancestor version and is used solely for human inspection and graph traversal. The `EXCLUDE` constraint is keyed on `logical_id`, not `id`.

**Rationale**: Decoupling the per-version PK from the cross-version logical identifier (a) keeps existing FKs from other tables stable when they reference the active row by `id`, (b) gives the recompute path an unambiguous handle (`logical_id + version`) that survives a re-publish, (c) matches the F04 markdown text ("conserve le `parent_id` ou la chaîne de versions").

**Alternatives considered**:
- Reuse `id` as the logical key + suffix `_version` columns — rejected: breaks every existing FK from non-versioned tables.
- Composite PK `(logical_id, version)` — rejected: adds friction to existing F01 FK relationships.

## R5. Temporal overlap invariant — DB enforcement

**Decision**: `EXCLUDE USING gist (logical_id WITH =, tstzrange(valid_from, COALESCE(valid_to, 'infinity'::timestamptz), '[)') WITH &&)` on each versioned table, requiring the `btree_gist` extension. Migration `0004` issues `CREATE EXTENSION IF NOT EXISTS btree_gist;` (idempotent, owned by the `migrator` role).

**Rationale**: GiST `EXCLUDE` constraints natively enforce temporal non-overlap and are the standard Postgres pattern. The half-open `[valid_from, valid_to)` interval models the semantics ("v2.3 active *up to but not including* v3.0's `valid_from`") so simultaneous boundaries do not overlap.

**Alternatives considered**:
- Trigger-based check — rejected: less expressive, slower under contention, harder to reason about.
- Application-layer check only — rejected: a concurrent transaction can still create an overlap window.

## R6. Optimistic lock surface

**Decision**: Use the HTTP `If-Match` header carrying the integer `version` of the row at the time of read. The `publish_new_version` helper compares `If-Match` against the current row inside a `SELECT ... FOR UPDATE` transaction; on mismatch it raises `OptimisticLockError` and the API returns HTTP 412 with a structured body `{error: "version_conflict", current_version: <n>}`.

**Rationale**: `If-Match` is the textbook HTTP optimistic-lock pattern; integer versions are simpler than ETags here because the constitution already requires `version` to exist on every versioned row. Wrapping the check in `FOR UPDATE` prevents lost updates without introducing a global lock.

**Alternatives considered**:
- ETag with row hash — rejected: more code, no functional benefit when integer version exists.
- DB-level `xmin` MVCC token — rejected: not stable across replicas / vacuum.

## R7. Snapshot JSON Schema v1

**Decision**: Schema declared in Python as a Pydantic v2 model `CandidatureSnapshotV1` (`extra='forbid'`) with required keys `schema_version` (literal `"1"`), `referentiel` `{logical_id, version, valid_from}`, `offre` `{id, criteres: [{logical_id, version}]}`, `projet_state: dict`, `scores` `{global: Money, per_critere: dict[str, Money]}`, `sources: list[{source_id, verified}]`. JSONB validation also enforced server-side via `jsonschema` against an exported JSON Schema (committed under `contracts/snapshot.schema.json`). The schema is *closed for removals, open for additions* — a future `schema_version='2'` MAY add keys but not delete v1 keys.

**Rationale**: A Pydantic model gives compile-time-ish guarantees in Python and produces the JSON Schema for free. Version pinning (`schema_version='1'`) lets F25/F26 evolve without breaking historical snapshots.

**Alternatives considered**:
- Free-form JSONB — rejected: defeats SC-003 (recompute parity).
- Versioned table with normalised columns — rejected: snapshot data is intrinsically heterogeneous and read-only.

## R8. Recompute drift handling

**Decision**: `POST /candidatures/{id}/recompute-from-snapshot` always returns HTTP 200 with body `{recomputed_score, snapshotted_score, drift_detected: bool, request_id}`. When drift exceeds 0.01 (any currency unit), the handler emits an audit event `entity_type='candidature', field='score_drift', source_of_change='system'` capturing both values, and the response sets `drift_detected: true`. No HTTP error: admin tooling must remain inspectable. A separate admin alert is emitted via the existing logger (no new infrastructure).

**Rationale**: Returning 4xx/5xx on drift would hide the diagnostic body from naive HTTP clients (curl, scripts). Recording an audit event keeps P3 satisfied and creates the ground truth that triggers monitoring downstream.

**Alternatives considered**:
- HTTP 409 — rejected per clarify session.
- Silent log only — rejected: leaves no auditable trace.

## R9. Pagination, ordering, and indexing for `audit_log` reads

**Decision**: Index `audit_log_account_entity_ts_idx` on `(account_id, entity_type, entity_id, timestamp DESC, id DESC)` plus a partial index `audit_log_account_ts_idx` on `(account_id, timestamp DESC, id DESC)` for unfiltered tenant scans. API ordering: `timestamp DESC, id DESC` (ties broken by `id` to keep keyset pagination stable). Pagination defaults to `page_size=20`, max `100`. Admins issuing cross-tenant queries hit the secondary index `audit_log_admin_ts_idx` on `(timestamp DESC, id DESC)` (small overhead, justified for compliance queries).

**Rationale**: Composite indexes mirror the most frequent filter shapes and satisfy SC-005 / SC-006 on a 1 M-row tenant.

**Alternatives considered**:
- Single big index on (account_id, timestamp DESC) — rejected: insufficient for entity-level drilldowns.
- Partitioning per month — rejected for MVP (out of scope per spec).

## R10. RLS policy shape on `audit_log`

**Decision**:
```sql
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_log_tenant_isolation ON audit_log
  FOR SELECT USING (
    account_id = current_setting('app.current_account_id', true)::uuid
    OR current_setting('app.current_role', true) = 'admin'
  );
CREATE POLICY audit_log_insert_only ON audit_log
  FOR INSERT WITH CHECK (true);
CREATE POLICY audit_log_no_update ON audit_log FOR UPDATE USING (false);
CREATE POLICY audit_log_no_delete ON audit_log FOR DELETE USING (false);
```
Combined with `REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM app_user, PUBLIC;`.

**Rationale**: Belt-and-braces — privileges block at the relational layer, RLS blocks at the row layer. `app.current_role` follows the F02 convention; admins bypass tenant filtering on read only.

## R11. Privacy redaction in old/new values

**Decision**: A configurable blacklist (`AUDIT_REDACTION_FIELDS`, default `password`, `password_hash`, `jwt`, `access_token`, `refresh_token`, `secret`, `api_key`) is applied **inside `record_audit`** before the row is inserted. The redaction recursively walks the JSON document and replaces any matching key's value with the literal string `"[REDACTED]"`. Unit-tested by a fuzz test that injects each blacklisted field name at every nesting depth.

**Rationale**: Centralised redaction prevents a forgetful caller from leaking secrets. Unit-level fuzz testing satisfies SC-010.

## R12. Frontend badge implementation

**Decision**: A Vue 4 SFC `<VersionBadge>` accepting props `referentielName: string`, `version: number`, `validFrom: string` (ISO date). It renders `Évalué selon Référentiel {{ referentielName }} v{{ version }} du {{ formattedDate }}` where `formattedDate` is the `validFrom` formatted as `dd/MM/yyyy` via the native `Intl.DateTimeFormat('fr-FR')`. No external date library.

**Rationale**: Native `Intl` keeps the bundle small; French is the only target locale per constitution.

## R13. Performance test approach

**Decision**: A `pytest` perf test (gated by env var `RUN_PERF=1`) inserts 10 000 audit rows over 100 seconds while running 10 concurrent reads/sec; asserts insert throughput ≥ 100/s and read p95 ≤ 200 ms. Postgres runs in the standard project Docker container (single instance, default `pgvector/pgvector:pg16`).

**Rationale**: SC-005 must be verifiable on a developer machine without exotic tooling. Gating prevents CI flakiness on small runners.

## R14. Out-of-MVP follow-ups (recorded for traceability)

- Time-based partitioning of `audit_log` once the table exceeds ~10 M rows (post-MVP).
- Archive role with `DELETE` privilege on `audit_log` for retention purges (post-MVP).
- "Diff between two referential versions" admin UI (post-MVP).
- Timeline visualisation of historical changes (post-MVP).
- Internationalisation of `<VersionBadge>` (post-MVP).
