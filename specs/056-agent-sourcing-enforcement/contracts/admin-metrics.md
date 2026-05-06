# Contract — Admin Metrics Endpoint (FR-013)

**Status**: Phase 1 (canonical)

## Endpoint

```
GET /admin/agent/metrics/sourcing?period={7d|30d|all}
```

**Auth**: Bearer token, role `Admin` only (FastAPI dependency).
**Rate limit**: 60 req/min/admin (SlowAPI).

## Query parameters

| Name      | Type       | Default | Description |
|-----------|------------|---------|-------------|
| period    | enum       | `7d`    | Time window: `7d`, `30d`, `all`.    |

## Response

### 200 OK

```json
{
  "period": "7d",
  "computed_at": "2026-05-06T18:00:00Z",
  "compliance_rate": 0.87,
  "unsourced_rate": 0.04,
  "retry_rate": 0.06,
  "fallback_rate": 0.01,
  "total_runs": 1200,
  "runs_with_citation": 1044,
  "runs_with_unsourced": 48,
  "runs_with_retry": 72,
  "runs_with_fallback": 12,
  "top_sources": [
    {"source_id": "uuid", "title": "ADEME Base Carbone v23.5", "publisher": "ADEME", "citation_count": 432}
  ],
  "top_unsourced_topics": [
    {"claim": "Le seuil GCF pour les PME est de 50 M USD", "count": 12, "first_seen": "2026-04-29T10:00:00Z"}
  ]
}
```

### Schema (Pydantic v2)

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID

class TopSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID
    title: str
    publisher: str
    citation_count: int = Field(ge=0)

class TopUnsourcedTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str
    count: int = Field(ge=0)
    first_seen: datetime

class SourcingMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: Literal["7d", "30d", "all"]
    computed_at: datetime
    compliance_rate: float = Field(ge=0.0, le=1.0)
    unsourced_rate: float = Field(ge=0.0, le=1.0)
    retry_rate: float = Field(ge=0.0, le=1.0)
    fallback_rate: float = Field(ge=0.0, le=1.0)
    total_runs: int = Field(ge=0)
    runs_with_citation: int = Field(ge=0)
    runs_with_unsourced: int = Field(ge=0)
    runs_with_retry: int = Field(ge=0)
    runs_with_fallback: int = Field(ge=0)
    top_sources: list[TopSource] = Field(max_length=20)
    top_unsourced_topics: list[TopUnsourcedTopic] = Field(max_length=20)
```

## Errors

| Status | Code                | Body                                      |
|--------|---------------------|-------------------------------------------|
| 401    | unauthorized        | `{"error":"unauthenticated"}`             |
| 403    | forbidden           | `{"error":"admin_role_required"}`         |
| 422    | validation_error    | Pydantic detail array                     |
| 500    | internal_error      | `{"error":"internal_error","detail":...}` |

## Compute logic

```sql
-- compliance_rate = runs with ≥1 cite_source / total runs
SELECT count(*) AS total, sum(CASE WHEN sources_cnt > 0 THEN 1 ELSE 0 END) AS with_cite
FROM (
  SELECT a.id,
    (SELECT count(*) FROM tool_call_log
     WHERE agent_run_id = a.id AND tool_name = 'cite_source' AND status = 'ok') AS sources_cnt
  FROM agent_run a
  WHERE a.created_at >= :since
) t;

-- retry_rate = runs with sourcing_retry_count >= 1 / total
SELECT
  count(*) AS total,
  sum(CASE WHEN sourcing_status = 'retried_ok' OR sourcing_status = 'failed' THEN 1 ELSE 0 END) AS retried
FROM agent_run WHERE created_at >= :since;

-- fallback_rate = runs with sourcing_status='failed' / total
SELECT count(*) FROM agent_run WHERE sourcing_status = 'failed' AND created_at >= :since;

-- top_sources from chat_message.sources (JSONB -> citation_count)
SELECT (s->>'source_id')::uuid AS source_id, count(*) AS citation_count
FROM chat_message m, jsonb_array_elements(m.sources) AS s
WHERE m.created_at >= :since
GROUP BY (s->>'source_id')::uuid
ORDER BY citation_count DESC
LIMIT 20;

-- top_unsourced_topics from unsourced_flag (admin bypasses RLS via app.current_account_id sentinel)
SELECT lower(claim) AS claim, count(*) AS count, min(created_at) AS first_seen
FROM unsourced_flag
WHERE created_at >= :since AND resolved_at IS NULL
GROUP BY lower(claim)
ORDER BY count DESC
LIMIT 20;
```

## Caching

- 5-minute Redis cache (key `admin:metrics:sourcing:{period}`).
- Fallback to live query on cache miss.

## Security

- Endpoint MUST be gated by `dependency=admin_required` (FastAPI dependency from `app/auth/admin.py`).
- Cross-tenant queries use a sentinel admin context (`app.current_account_id = '00000000-0000-0000-0000-000000000000'` or temporary `SET LOCAL ROLE app_admin`).
- All requests are audited via the existing admin audit pipeline (admin user_id + endpoint name).

## OpenAPI fragment

```yaml
paths:
  /admin/agent/metrics/sourcing:
    get:
      summary: F56 — Sourcing compliance metrics
      operationId: getSourcingMetrics
      tags: [admin, agent]
      security: [{BearerAuth: []}]
      parameters:
        - name: period
          in: query
          required: false
          schema:
            type: string
            enum: [7d, 30d, all]
            default: 7d
      responses:
        '200':
          description: Sourcing compliance metrics
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SourcingMetricsResponse'
        '403':
          description: Admin role required
        '500':
          description: Internal error
```
