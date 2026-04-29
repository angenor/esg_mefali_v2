# Data Model — F04 Audit Log Append-Only & Versioning

**Feature**: 004-audit-log-versioning
**Date**: 2026-04-29

## Overview

This feature introduces one new table (`audit_log`), one new Postgres ENUM (`source_of_change_t`), four new columns on each of the seven versioned catalogue tables, one EXCLUDE constraint per versioned table, and two new columns on the existing `candidature` table.

## 1. New ENUM `source_of_change_t`

```sql
CREATE TYPE source_of_change_t AS ENUM (
    'manual',  -- direct user action via API
    'llm',     -- mutation issued by an LLM tool (via decorator)
    'import',  -- bulk import / migration script with provenance
    'admin',   -- admin override
    'system'   -- internal background job, no user attribution
);
```

## 2. New table `audit_log`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | Monotonic insert order. |
| `user_id` | `UUID` | NULL | NULL for `system` events. References `users(id)` (no FK enforced — preserves history if user deleted). |
| `account_id` | `UUID` | NULL | NULL for `system` global events. RLS pivot. |
| `timestamp` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | Server-side. |
| `entity_type` | `TEXT` | NOT NULL | E.g. `entreprise`, `projet`, `candidature`, `referentiel`. |
| `entity_id` | `UUID` | NOT NULL | Logical id (or row id) of the touched entity. |
| `field` | `TEXT` | NULL | NULL for entity-level events (insert/delete). |
| `old_value` | `JSONB` | NULL | Redacted via blacklist. NULL on insert. |
| `new_value` | `JSONB` | NULL | Redacted via blacklist. NULL on delete. |
| `source_of_change` | `source_of_change_t` | NOT NULL | Enum-bounded. |
| `request_id` | `TEXT` | NOT NULL | Correlation id propagated from middleware. |
| `ip` | `INET` | NULL | Originating IP. |
| `notes` | `TEXT` | NULL | Free-form context (e.g. job name). |

**Indexes**:
- `audit_log_account_entity_ts_idx` BTREE `(account_id, entity_type, entity_id, timestamp DESC, id DESC)`
- `audit_log_account_ts_idx` BTREE `(account_id, timestamp DESC, id DESC) WHERE account_id IS NOT NULL`
- `audit_log_admin_ts_idx` BTREE `(timestamp DESC, id DESC)` (cross-tenant admin queries)
- `audit_log_request_id_idx` BTREE `(request_id)` for incident correlation.

**RLS**:
```sql
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_log_tenant_isolation ON audit_log
  FOR SELECT USING (
    current_setting('app.current_role', true) = 'admin'
    OR account_id = current_setting('app.current_account_id', true)::uuid
  );
CREATE POLICY audit_log_insert_any ON audit_log
  FOR INSERT WITH CHECK (true);
CREATE POLICY audit_log_no_update ON audit_log FOR UPDATE USING (false);
CREATE POLICY audit_log_no_delete ON audit_log FOR DELETE USING (false);
```

**Privileges**:
```sql
GRANT INSERT, SELECT ON audit_log TO app_user;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM app_user, PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO app_user;
```

## 3. Versioned-table additions

For each of `referentiel`, `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`:

| Column | Type | Constraints |
|---|---|---|
| `version` | `INT` | NOT NULL DEFAULT 1, CHECK (`version >= 1`) |
| `valid_from` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` |
| `valid_to` | `TIMESTAMPTZ` | NULL, CHECK (`valid_to IS NULL OR valid_to > valid_from`) |
| `parent_id` | `UUID` | NULL, FK → same table `(id)` ON DELETE RESTRICT |
| `logical_id` | `UUID` | NOT NULL DEFAULT `gen_random_uuid()` |

**Backfill**: existing F01 rows receive `version=1`, `valid_from=created_at`, `valid_to=NULL`, `parent_id=NULL`, `logical_id=gen_random_uuid()`.

**Index per table**: `<tbl>_logical_active_idx` BTREE `(logical_id) WHERE valid_to IS NULL` for fast `get_active`.

**Temporal-overlap invariant** (per table):
```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE referentiel
  ADD CONSTRAINT referentiel_no_temporal_overlap
  EXCLUDE USING gist (
    logical_id WITH =,
    tstzrange(valid_from, COALESCE(valid_to, 'infinity'::timestamptz), '[)') WITH &&
  );
-- repeated for each of the 7 tables
```

## 4. `candidature` table additions

| Column | Type | Constraints |
|---|---|---|
| `snapshot_json` | `JSONB` | NULL initially; NOT NULL once `submitted_at` is set; immutable post-submission via DB trigger `candidature_snapshot_immutable_trg`. |
| `submitted_at` | `TIMESTAMPTZ` | NULL until the `submitted` transition. |

**Immutability trigger**:
```sql
CREATE OR REPLACE FUNCTION candidature_snapshot_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.submitted_at IS NOT NULL
     AND (NEW.snapshot_json IS DISTINCT FROM OLD.snapshot_json
          OR NEW.submitted_at IS DISTINCT FROM OLD.submitted_at) THEN
    RAISE EXCEPTION 'snapshot_json and submitted_at are immutable after submission'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER candidature_snapshot_immutable_trg
BEFORE UPDATE ON candidature
FOR EACH ROW EXECUTE FUNCTION candidature_snapshot_guard();
```

The application layer additionally rejects mutation attempts at the API boundary and records an `integrity_violation_attempt` audit event.

## 5. Pydantic models (backend)

```python
class CandidatureSnapshotV1(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1']
    referentiel: ReferentielRef       # logical_id, version, valid_from
    offre: OffreRef                    # id, criteres: list[CritereRef]
    projet_state: dict[str, Any]
    scores: SnapshotScores             # global: Money, per_critere: dict[str, Money]
    sources: list[SourceRef]           # source_id, verified

class AuditLogEntryIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    entity_type: str
    entity_id: UUID
    field: str | None
    old_value: Any | None
    new_value: Any | None
    source_of_change: SourceOfChange   # Enum mirror of source_of_change_t
    request_id: str
    notes: str | None = None

class AuditLogEntryOut(AuditLogEntryIn):
    id: int
    user_id: UUID | None
    account_id: UUID | None
    timestamp: datetime
    ip: str | None
```

## 6. SQLAlchemy mixin

```python
class VersionedMixin:
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valid_from: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    valid_to: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey(f"{__tablename__}.id"), nullable=True)
    logical_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'))
```

## 7. State transitions

### Versioned entity lifecycle

```
[ACTIVE (valid_to IS NULL)]
        | publish_new_version(new_payload, version_at_load)
        v
[CLOSED (valid_to = T, ACTIVE row replaced by new version with parent_id = closed.id)]
```

### Candidature snapshot lifecycle

```
[draft]    (snapshot_json IS NULL, submitted_at IS NULL)
   | submit()
   v
[submitted](snapshot_json populated atomically, submitted_at = now())
   | recompute-from-snapshot (read-only, no state change)
   v
[submitted](unchanged; possibly emits drift audit event)
```

## 8. Cross-feature relationships

- F01 supplies the seven catalogue tables and the `candidature` table; F04 only ALTERs them.
- F02 supplies `app_user`, `migrator`, RLS middleware setting `app.current_account_id` and `app.current_role`; F04 reuses both.
- F03 supplies the `source` catalogue (`verified` status); F04's snapshot references existing `source.id` values without duplicating them.
- F17 (later) consumes the `@journal_llm_mutation` decorator delivered here.
- F23 (later) provides the scoring logic used by `recompute_from_snapshot`; F04 ships only the recompute orchestration shell — the scoring function is imported at runtime and treated as an opaque dependency in MVP testing (mocked).
