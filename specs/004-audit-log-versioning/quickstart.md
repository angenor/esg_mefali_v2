# Quickstart — F04 Audit Log & Versioning

## Prerequisites

- F01 + F02 + F03 merged to `main` (current state).
- Postgres docker container running (`docker compose up -d db`).
- Backend `.venv` activated; deps installed (`pip install -r backend/requirements.txt`).
- Frontend deps installed (`pnpm install` in `frontend/`).

## Apply migration

```bash
cd backend
alembic upgrade head     # runs 0004_audit_log_and_versioning.py
```

This creates `audit_log`, the `source_of_change_t` ENUM, alters the seven versioned tables, adds the EXCLUDE constraints, and adds `snapshot_json` + `submitted_at` to `candidature`.

## Verify append-only privileges

```bash
psql -U app_user -h localhost -d esg_mefali -c \
  "UPDATE audit_log SET notes='hack' WHERE id=1;"
# expected: ERROR:  permission denied for table audit_log
psql -U app_user -h localhost -d esg_mefali -c \
  "DELETE FROM audit_log WHERE id=1;"
# expected: ERROR:  permission denied for table audit_log
```

## Use the helper from a service

```python
from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange

await record_audit(
    session=session,
    entity_type="entreprise",
    entity_id=entreprise.id,
    field="nom",
    old_value=old_nom,
    new_value=new_nom,
    source_of_change=SourceOfChange.MANUAL,
)
```

## Decorate an LLM tool handler (consumed by F17 later)

```python
from app.audit.decorator import journal_llm_mutation

@journal_llm_mutation(entity_type="projet")
async def update_projet_status(args: UpdateProjetStatusArgs, ctx: ToolContext) -> ProjetOut:
    ...
```

## Publish a new referential version

```bash
curl -X POST http://localhost:8000/api/v1/referentiels/<logical_id>/publish \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "If-Match: 2" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"name":"GCF","code":"GCF","description":"v3.0 ..."}}'
```

Stale `If-Match` returns HTTP 412 with `{"error":"version_conflict","current_version":3}`.

## Recompute a candidature score from snapshot

```bash
curl -X POST http://localhost:8000/api/v1/candidatures/<id>/recompute-from-snapshot \
  -H "Authorization: Bearer $ADMIN_JWT"
```

Response:
```json
{
  "recomputed_score": { "global": {"amount":"83.50","currency":"PCT"}, "per_critere": {} },
  "snapshotted_score":{ "global": {"amount":"83.50","currency":"PCT"}, "per_critere": {} },
  "drift_detected": false,
  "request_id": "req_abc123"
}
```

## Frontend badge usage

```vue
<template>
  <VersionBadge
    referentiel-name="GCF"
    :version="2"
    valid-from="2026-03-15T00:00:00Z"
  />
</template>
```

Renders: `Évalué selon Référentiel GCF v2 du 15/03/2026`.

## Run tests

```bash
# Backend
cd backend && pytest tests/unit/audit tests/unit/versioning tests/unit/snapshot -q
cd backend && pytest tests/integration -q
RUN_PERF=1 pytest backend/tests/perf -q     # SC-005

# Frontend
cd frontend && pnpm vitest run tests/unit/VersionBadge.spec.ts

# E2E
pnpm playwright test e2e/test_recompute_from_snapshot_flow.spec.ts
```

## Validation checklist

- [ ] `audit_log` exists, RLS enabled, `app_user` cannot UPDATE/DELETE.
- [ ] All seven versioned tables have `version`, `valid_from`, `valid_to`, `parent_id`, `logical_id`, and the `EXCLUDE` constraint.
- [ ] `candidature.snapshot_json` is non-null on submitted rows; immutability trigger active.
- [ ] `record_audit` redacts blacklisted fields.
- [ ] `publish_new_version` rejects stale `If-Match` with HTTP 412.
- [ ] `recompute-from-snapshot` returns 200 with both scores and `drift_detected`.
- [ ] `<VersionBadge>` renders the French string.
