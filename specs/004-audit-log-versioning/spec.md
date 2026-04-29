# Feature Specification: Audit Log Append-Only & Versioning

**Feature Branch**: `004-audit-log-versioning`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F04 — Audit Log Append-Only & Versioning (Phase 0, Modules 0.4 + 0.5). Two transversal invariants: (1) append-only audit log of every business mutation with who/when/what/old/new/source; (2) versioning of Référentiels and immutable Candidature snapshots so a submission against GCF v2.3 in 2026 remains defensible in 2028 even if GCF moved to v3.0."

## Clarifications

### Session 2026-04-29

- Q: Should `audit_log` be a single global table (RLS-filtered) or partitioned per tenant in MVP? → A: Single global table with RLS by `account_id` (mirrors F02 convention; aligns with append-only privilege model)
- Q: What is the minimum required key set of `snapshot_json` schema v1 delivered by F04? → A: `schema_version`, `referentiel` `{id, version, valid_from}`, `offre` `{id, criteres: [{id, version}]}`, `projet_state` (opaque blob), `scores` `{global, per_critere}`, `sources` (array of source ids+verified flags) — F25/F26 may extend, never remove
- Q: How are versioned tables identified across versions (logical key for `parent_id` chain)? → A: Add a dedicated `logical_id UUID NOT NULL` column on each versioned table (separate from row PK `id`), filled at first version with a fresh UUID and copied to every subsequent version
- Q: Audit-log retention in MVP (no purge role, but can rows be cold-archived)? → A: Keep all rows hot in the primary table for the entire MVP; no archival, no TTL; partitioning + cold storage explicitly post-MVP
- Q: When `recompute-from-snapshot` produces a drift > 0.01, should the endpoint return 200 with warning, or 409? → A: Return HTTP 200 with both scores in the body AND a `drift_detected: true` flag; record an `integrity_violation_attempt` audit event; do NOT 409 (admin tooling must remain inspectable)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every business mutation is journaled (Priority: P1)

The compliance team needs every insert, update, or delete on business tables (Entreprise, Projet, Candidature, Score, Attestation, etc.) to be recorded in an append-only `audit_log` capturing who, when, what entity, what field, the old and new values, and the source of the change. This is quasi-regulatory in finance and is the only way to defend the platform in case of audit or litigation.

**Why this priority**: Without this, no other feature can be trusted in production — auditors cannot reconstruct history, and disputes cannot be resolved. It is invariant 3 of Module 0.

**Independent Test**: Modify a single field of an Entreprise via the API as an authenticated PME user. Verify a new row appears in `audit_log` with the expected `entity_type`, `entity_id`, `field`, `old_value`, `new_value`, `source_of_change='manual'`, `user_id`, `account_id`, `timestamp`. Then attempt `UPDATE audit_log SET ...` and `DELETE FROM audit_log` from the application database role — both must fail with a privilege error.

**Acceptance Scenarios**:

1. **Given** a PME user authenticated on tenant A with an existing Entreprise record, **When** they update the `nom` field via the API, **Then** exactly one new `audit_log` row is created with `entity_type='entreprise'`, `field='nom'`, the previous and new values, `source_of_change='manual'`, the user's id, the tenant's `account_id`, and a server-side timestamp.
2. **Given** the application database role, **When** any `UPDATE audit_log` or `DELETE FROM audit_log` statement is attempted, **Then** the database rejects the statement with a privilege error and no row is altered.
3. **Given** a creation of a new Projet by a PME user, **When** the create operation succeeds, **Then** an `audit_log` row records the insert with `old_value=NULL`, `new_value` containing the inserted snapshot, and `field=NULL` (entity-level event).

---

### User Story 2 - The source of every change is traceable (Priority: P1)

Auditors and the engineering team need to distinguish whether a mutation came from a manual user input, from a LLM-driven tool execution, from an import, from an admin override, or from a system process. This makes it possible to analyse error and behavioural patterns of the LLM and to attribute responsibility cleanly.

**Why this priority**: Without `source_of_change`, the audit log cannot answer the most important compliance question — "did a human or a machine do this?". It is also the foundation that the LLM mutation tools (F17) depend on.

**Independent Test**: Insert audit rows from each of the five contexts (manual user action, LLM tool decorator, import script, admin override, system migration) and verify each row carries the correct `source_of_change` enum value. Attempt to insert an unknown enum value — must be rejected.

**Acceptance Scenarios**:

1. **Given** the helper invoked from a manual API handler, **When** it records a mutation, **Then** `source_of_change='manual'`.
2. **Given** the helper invoked through the LLM mutation decorator, **When** it records a mutation, **Then** `source_of_change='llm'`.
3. **Given** an attempted insert with `source_of_change='unknown'`, **When** the database receives it, **Then** the insert is rejected by the enum constraint.

---

### User Story 3 - The PME consults the history of its own actions (Priority: P2)

A PME user wants a read-only "Action history" view listing every modification made on its own data — by itself, by its collaborators, and by the LLM acting on its behalf. The view is paginated and filterable by entity type, entity id, source of change, and date range. Strict tenant isolation must be enforced: the PME never sees another tenant's events.

**Why this priority**: Important for trust and transparency, but the platform can ship the audit infrastructure (P1) before exposing the consumer view. Will be visually integrated by F32 (PME dashboard).

**Independent Test**: As a PME on tenant A, query the audit-log endpoint with several filter combinations and verify only tenant A's rows are returned, paginated, and ordered by timestamp descending. As an admin, verify cross-tenant access is allowed.

**Acceptance Scenarios**:

1. **Given** PME user on tenant A with 50 audit events on its data and tenant B with 30 events, **When** the PME calls `GET /audit-log?page=1&page_size=20`, **Then** the response contains only tenant A events, ordered newest first, with pagination metadata.
2. **Given** an admin user, **When** they call `GET /audit-log?account_id=B`, **Then** they receive tenant B's events.
3. **Given** a PME user, **When** they request an export of their audit log in CSV or JSON format, **Then** the export contains only their tenant's rows.

---

### User Story 4 - Référentiels are versioned over time (Priority: P1)

The taxonomy of each Référentiel (GCF, BOAD, UEMOA, etc.) evolves. Each Référentiel must carry `version`, `valid_from`, and `valid_to` so that historical scores and candidatures remain calculable against the version that was active at the time. Publishing a new version must atomically close the previous one without temporal gap or overlap.

**Why this priority**: Without versioning, every taxonomy change silently invalidates years of past scores and breaks audit defensibility. It is invariant 4 of Module 0.

**Independent Test**: Insert Référentiel GCF v2.3 with `valid_from=2025-01-01, valid_to=NULL`. Publish GCF v3.0 via the helper. Verify v2.3 now has `valid_to` set to the publication timestamp and v3.0 has `valid_from` equal to the same timestamp with `valid_to=NULL`. Run the SQL invariant check: there must be no two rows with overlapping validity windows for the same logical referentiel.

**Acceptance Scenarios**:

1. **Given** GCF v2.3 active (`valid_from=2025-01-01, valid_to=NULL`), **When** an admin publishes GCF v3.0 via the publish helper, **Then** v2.3 is closed (`valid_to` = publish timestamp), v3.0 is opened (`valid_from` = same timestamp, `valid_to=NULL`), and `version` increments by 1.
2. **Given** a query `get_active('referentiel', id, at_timestamp=2026-03-15)`, **When** GCF was at v2.3 on that date and v3.0 was published 2026-04-01, **Then** the helper returns v2.3.
3. **Given** two admins simultaneously edit GCF v2.3, **When** the second one tries to publish a new version with a stale `version_at_load`, **Then** the request is rejected with an optimistic-lock error (HTTP 412 Precondition Failed).

---

### User Story 5 - Critères, Indicateurs, Formules, Seuils, Templates are versioned (Priority: P1)

The same `version + valid_from + valid_to` pattern is required on every sub-object of the referentials (`indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`) so that fine-grained changes (e.g. a single threshold revision) are traceable.

**Why this priority**: Same compliance and historical defensibility motivations as US4. Without it, a change to a single Seuil silently shifts past scores.

**Independent Test**: Apply the version-publish flow to a single `seuil` row. Verify the closure of the prior version and the opening of the new one with the correct `parent_id` chain. Run the temporal-overlap invariant SQL on each versioned table.

**Acceptance Scenarios**:

1. **Given** a `seuil` row at version 1, **When** the publish helper creates version 2, **Then** version 1 has `valid_to` set, version 2 has `valid_from` set to the same instant, both share the same logical key, and the `parent_id` of v2 points to v1.
2. **Given** all versioned tables, **When** the temporal overlap invariant SQL is run, **Then** zero overlapping rows are found per logical key.

---

### User Story 6 - Candidatures store an immutable snapshot at submission (Priority: P1)

When a Candidature is submitted, a frozen JSON snapshot is attached containing: the project state, the offer's criteria, the active referential identifier and version, the calculated scores, and the source citations mobilised to compute those scores. This snapshot must remain valid even if the underlying referential evolves later.

**Why this priority**: Defensibility of past submissions is a hard regulatory requirement. Without the snapshot, a candidature submitted in 2026 cannot be audited in 2028. It is the second pillar of invariant 4.

**Independent Test**: Submit a Candidature; verify `snapshot_json` is non-null, `submitted_at` is set, and the snapshot conforms to the declared JSON schema. Six months later (simulated by changing the referential version), call the recompute endpoint and verify the score returned is the same to the cent as the score originally captured in the snapshot.

**Acceptance Scenarios**:

1. **Given** a draft Candidature, **When** the PME submits it, **Then** `snapshot_json` is populated according to the declared schema, `submitted_at` is set server-side, and the original score is recorded inside the snapshot.
2. **Given** a submitted Candidature whose referential has since been updated, **When** an admin calls `POST /candidatures/{id}/recompute-from-snapshot`, **Then** the system recomputes the score using the snapshotted data and returns a value equal to the cent to the original score.
3. **Given** an admin attempts to mutate `snapshot_json` after submission, **When** the API receives the request, **Then** it is rejected because the field is immutable post-submission.

---

### User Story 7 - Version badge displayed in UI (Priority: P2)

End users see clearly against which version of a referential a score was calculated, e.g. "Évalué selon Référentiel GCF v2.3 du 15/03/2026". The badge is a reusable UI component.

**Why this priority**: Important for transparency and trust, but a cosmetic layer over P1 data plumbing.

**Independent Test**: Render the badge component with sample inputs and verify the displayed text matches the expected format in French.

**Acceptance Scenarios**:

1. **Given** a score computed against GCF v2.3 active on 2026-03-15, **When** the badge is rendered, **Then** it displays "Évalué selon Référentiel GCF v2.3 du 15/03/2026".

---

### Edge Cases

- **Long old/new value**: a JSONB old/new pair larger than the practical TOAST threshold (~1 MB) must still be stored, but the helper SHOULD truncate or reference an external blob if a payload exceeds 256 KB to keep the audit log lean.
- **Sensitive fields blacklisted**: any field whose name matches a configured blacklist (passwords, JWT, refresh tokens, cipher material) must be redacted to the literal string `"[REDACTED]"` in `old_value` / `new_value` before insertion. The helper itself enforces this — callers cannot opt out.
- **Anonymous mutations**: a mutation triggered by a system migration may have no `user_id`; in that case `user_id` is NULL but `source_of_change='system'` and `request_id` is required for traceability.
- **Multi-tenant isolation breach attempt**: a query with a forged `account_id` parameter from a PME user must still be filtered by RLS to the user's tenant, ignoring the parameter.
- **Snapshot referential reference missing**: if the helper cannot resolve `get_active(referentiel, id, at_timestamp)` because no version was active, the submission of the candidature is refused with a clear error rather than producing a partial snapshot.
- **Concurrent publication of two versions**: two admins publishing a new version of the same referential within the same instant — only one can succeed; the second receives the optimistic-lock error.
- **Recompute drift**: if the recompute endpoint produces a value different from the snapshotted score by more than 0.01 unit, the system records an integrity-violation audit event and surfaces an admin alert.
- **Audit log table reaches large volume**: the table must remain queryable under the index `(account_id, entity_type, entity_id, timestamp DESC)` without degradation; partitioning is post-MVP.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST persist every business mutation in an append-only `audit_log` table whose row schema captures: an autogenerated id, the acting user id (nullable), the tenant `account_id` (nullable for system events), a server-side timestamp, the entity type, the entity id, an optional field name, the prior value as structured JSON, the new value as structured JSON, the `source_of_change` enum, the request correlation id, the originating IP (nullable), and free-form notes.
- **FR-002**: The system MUST grant the application database role `INSERT` privilege on `audit_log` and MUST revoke `UPDATE`, `DELETE`, and `TRUNCATE` privileges on it; only a separate archive role (out of MVP scope) may purge rows.
- **FR-003**: The backend MUST provide a single helper `record_audit(entity_type, entity_id, field?, old, new, source_of_change, ...)` that all business services invoke explicitly on every mutation. Database triggers MUST NOT be used to populate the audit log in the MVP.
- **FR-004**: The helper MUST be invokable by a Python decorator that wraps LLM mutation tool handlers (consumed by F17) so that LLM-originated mutations are journaled with `source_of_change='llm'` without each tool needing to call the helper itself.
- **FR-005**: The system MUST expose `GET /audit-log` accepting filter parameters `entity_type`, `entity_id`, `from`, `to`, `source_of_change`, `page`, `page_size`. PME users see only their own tenant's rows (enforced by RLS); admins may filter across tenants.
- **FR-006**: The system MUST expose CSV and JSON export endpoints for the audit log restricted to the caller's tenant (or all tenants for admins) and respecting the same RLS policy.
- **FR-007**: The system MUST add `version INT NOT NULL DEFAULT 1`, `valid_from TIMESTAMPTZ NOT NULL DEFAULT now()`, `valid_to TIMESTAMPTZ NULL`, `parent_id` (FK to the previous version row of the same table, NULL for first version), and `logical_id UUID NOT NULL` (stable identifier shared by every version of the same logical entity, generated at first version and copied to subsequent versions) on every versioned table: `referentiel`, `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`.
- **FR-008**: The system MUST provide a helper `publish_new_version(entity_type, logical_id, new_payload, version_at_load)` that atomically: validates `version_at_load` matches the current row, sets `valid_to = now()` on the active row, inserts the new version with `version = previous_version + 1`, `valid_from = now()`, `valid_to = NULL`, and `parent_id = previous_id`. The whole operation MUST run in one transaction.
- **FR-009**: The system MUST provide `get_active(entity_type, logical_id, at_timestamp?)` returning the row whose validity window covers the timestamp (default `now()`); if none matches, the helper returns null.
- **FR-010**: The system MUST add `snapshot_json JSONB NOT NULL` and `submitted_at TIMESTAMPTZ NULL` to the `candidature` table; the snapshot MUST be populated atomically with the transition to the submitted state and MUST conform to JSON Schema v1 declared in this feature, whose required keys are: `schema_version` (string, value `"1"`), `referentiel` (object with `id`, `version`, `valid_from`), `offre` (object with `id` and `criteres` array of `{id, version}`), `projet_state` (opaque object capturing the project as submitted), `scores` (object with `global` numeric and `per_critere` map), and `sources` (array of `{source_id, verified}` references). Subsequent features (F25/F26) MAY extend the schema with additional keys but MUST NOT remove any v1 key.
- **FR-011**: The system MUST expose `POST /candidatures/{id}/recompute-from-snapshot` that recomputes the score from the snapshot alone (without touching live referentials). The endpoint MUST return HTTP 200 with a body containing `recomputed_score`, `snapshotted_score`, and `drift_detected: bool` (true when the absolute difference exceeds 0.01). When `drift_detected` is true, the endpoint MUST also record an `audit_log` row with entity_type `candidature`, field `score_drift`, source_of_change `system`, and the two values in `old_value`/`new_value`. The endpoint MUST NOT return an HTTP error on drift — admin tooling must remain inspectable.
- **FR-012**: The frontend MUST provide a Vue component `<VersionBadge :referentiel-id :version :date>` that renders the localised string "Évalué selon Référentiel <name> v<version> du <date>" in French (UI is French-only at this stage).
- **FR-013**: The audit-log helper MUST redact any field whose name is on a configurable blacklist (default: `password`, `password_hash`, `jwt`, `access_token`, `refresh_token`, `secret`, `api_key`) by replacing its value with the literal string `"[REDACTED]"` before insertion.
- **FR-014**: The system MUST reject (HTTP 412) any version-publication request whose `version_at_load` does not match the current row's `version`, using the `If-Match` HTTP header convention.
- **FR-015**: The system MUST refuse submission of a Candidature whose referential snapshot cannot be resolved at the time of submission; the error MUST identify the missing referential and the timestamp queried.
- **FR-016**: The system MUST mark `snapshot_json` and `submitted_at` as immutable after submission; any attempt to modify them through the application APIs MUST be rejected.
- **FR-017**: The audit-log endpoint MUST support pagination with default `page_size=20` and a maximum of `100`; results MUST be ordered by `timestamp DESC, id DESC` for stable pagination.
- **FR-018**: Every mutation event MUST carry a `request_id` propagated from the inbound HTTP request (or generated for system mutations); the `request_id` MUST be returned in API responses to allow operators to correlate logs.
- **FR-019**: The helper MUST silently skip rather than fail when `old == new` (no-op mutation), to keep the log clean, and MUST log a debug-level message when this happens.
- **FR-020**: The system MUST enforce, at the database level (e.g. an `EXCLUDE` constraint or equivalent invariant), that no two rows of the same versioned table share the same `logical_id` and have overlapping `[valid_from, valid_to)` windows.
- **FR-021**: The `audit_log` MUST be implemented as a single global table whose rows are scoped per tenant via the `account_id` column and protected by Row-Level Security policies that filter by `app.current_account_id`, mirroring the convention established by F02. No per-tenant table partitioning is introduced in MVP.
- **FR-022**: All `audit_log` rows MUST remain in the primary table for the entire MVP duration: no archival, no TTL, no automatic purge. Cold-storage and partitioning strategies are explicitly post-MVP.

### Key Entities

- **AuditLogEntry**: Append-only journal entry. Attributes: `id`, `user_id`, `account_id`, `timestamp`, `entity_type`, `entity_id`, `field` (nullable), `old_value` (JSON), `new_value` (JSON), `source_of_change` (enum: `manual`, `llm`, `import`, `admin`, `system`), `request_id`, `ip` (nullable), `notes` (nullable). Tenant-scoped via `account_id`. Append-only at the privilege level.
- **VersionedEntity** (mixin applied to `referentiel`, `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`): adds `version`, `valid_from`, `valid_to`, `parent_id`. Logical identity is preserved across versions through a `logical_id` (or equivalent grouping key).
- **CandidatureSnapshot**: A JSON document attached to a `candidature` at submission. Contains: schema version, project state, offer criteria with id+version, referential id+version active at submission, computed scores, and source citations. Immutable after submission.
- **VersionBadge** (UI presentation entity): renders `referentiel name + version + date` in French.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of business mutations exercised by the integration test suite produce exactly one corresponding `audit_log` row with a non-null `source_of_change`.
- **SC-002**: Any `UPDATE` or `DELETE` statement against `audit_log` issued from the application database role fails with a privilege error in 100% of attempts (verified by automated test).
- **SC-003**: A Candidature submitted today and re-computed from its snapshot one year later returns a score equal to the original score within 0.01 unit (i.e. "to the cent") in 100% of seeded test cases.
- **SC-004**: After publishing 100 successive new versions of a single Référentiel, the temporal-overlap invariant SQL returns zero overlapping rows.
- **SC-005**: The `audit_log` insert path sustains at least 100 inserts per second on the developer Postgres container while a parallel read workload of 10 queries per second runs without read latency exceeding 200 ms at the 95th percentile.
- **SC-006**: A PME user querying their own audit log receives the first page (up to 20 events) in under 500 ms at the 95th percentile, on a tenant containing up to 1 million audit rows total.
- **SC-007**: Cross-tenant data leakage tests (PME of tenant A querying with `account_id=B`) return zero rows of tenant B in 100% of attempts.
- **SC-008**: An admin attempting to mutate `snapshot_json` post-submission is refused in 100% of attempts, and an `audit_log` event of type `integrity_violation_attempt` is recorded.
- **SC-009**: The optimistic-lock conflict (concurrent referential publication) returns HTTP 412 with a structured error body in 100% of conflicting attempts.
- **SC-010**: All sensitive blacklisted fields appear as `"[REDACTED]"` in 100% of `audit_log` rows where such fields were involved (verified by a fuzz test that mutates fields with each blacklisted name).

## Assumptions

- Authentication, JWT/refresh, RLS middleware, and the Postgres roles `app_user` and `migrator` are already provided by F02; this feature reuses them and does not redefine them.
- The `app.current_account_id` session variable convention from F02 is used as the basis for both audit-log inserts and read-side RLS filtering.
- Source verification, `unsourced_claim_log`, and the `cite_source` / `search_source` / `flag_unsourced` tools are already provided by F03; the audit log records the resulting mutations but does not duplicate the source-tracking machinery.
- The 18 base tables with `account_id`, `Money`, and `vector(1024)` from F01 already exist; this feature alters versioned tables in place rather than creating new ones.
- The 7 versioned entity tables (`referentiel`, `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`) exist in the F01 baseline; the F04 migration adds the four columns (`version`, `valid_from`, `valid_to`, `parent_id`) plus the temporal-overlap invariant.
- The `candidature` table from F01 has a status enum that includes a `submitted` transition; F04 adds the snapshot column and ties it to that transition.
- The MVP stays single-language (French UI); badge text does not need i18n in this phase.
- The Phase 3 LLM mutation tools (F17) will adopt the decorator delivered by this feature; F04 itself does not implement those tools.
- The audit log is not partitioned in MVP; partitioning will be added when the table exceeds roughly 10 million rows.
- Automatic purge after a legal retention period is post-MVP; the helper provides the privilege model that makes future archival possible.
- The platform is closed (PME + Admin only); there is no public-API consumer of the audit log to consider.

## Dependencies

- **F01 — foundations-stack-init**: provides the base tables and column types.
- **F02 — auth-roles-rls**: provides `app_user` / `migrator` roles, RLS middleware, and the `app.current_account_id` session-variable convention.
- **F03 — source-anti-hallucination**: provides the source-tracking layer that audit events reference but do not duplicate.

## Out of Scope (MVP)

- Time-based partitioning of `audit_log`.
- Automatic purge after retention period.
- An admin "diff between two versions of a referential" UI.
- A full timeline visualisation of historical changes in the UI.
- Internationalisation of the version badge (French only at this stage).
- Implementation of the LLM mutation tools themselves (delivered by F17, which will consume the decorator from this feature).
