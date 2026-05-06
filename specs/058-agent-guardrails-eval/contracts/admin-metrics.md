# Contract: Admin Agent Metrics Consolidé (FR-020 — US9)

## GET `/admin/agent/metrics`

**Auth**: `require_admin`. Non-admin → 404 (P2 convention).

**Query params** :
- `period` : `7d` | `30d` | `all` (default `7d`).

**Response 200** :

```json
{
  "period": "7d",
  "computed_at": "2026-05-06T21:30:00Z",
  "runs": {
    "total": 1234,
    "error_rate": 0.012,
    "cancelled_rate": 0.005,
    "latency_p50_ms": 850,
    "latency_p95_ms": 2400
  },
  "tools": {
    "top_invocations": [
      {"tool_name": "cite_source", "invocations": 542, "validation_error_rate": 0.001},
      {"tool_name": "create_project", "invocations": 187, "validation_error_rate": 0.021},
      // ... top 10
    ]
  },
  "sourcing": {
    // Alimenté par le sous-endpoint /admin/agent/metrics/sourcing existant F56
    "compliance_rate": 0.92,
    "unsourced_rate": 0.08,
    "retry_rate": 0.05,
    "fallback_rate": 0.02
  },
  "security": {
    "injection_attempts_count": 17,
    "pii_masked_count": 234,
    "loop_detected_count": 2,
    "language_corrected_count": 8
  },
  "cost": {
    "tokens_in_total": 1456789,
    "tokens_out_total": 234567,
    "estimated_usd_per_day": 4.12
  },
  "memory": {
    "recall_hit_rate": 0.78,
    "compactions_count": 12
  }
}
```

## Pydantic response schemas

```python
class RunsSection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    total: int
    error_rate: float
    cancelled_rate: float
    latency_p50_ms: int
    latency_p95_ms: int

class ToolInvocation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool_name: str
    invocations: int
    validation_error_rate: float

class ToolsSection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    top_invocations: list[ToolInvocation]

class SourcingSection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    compliance_rate: float
    unsourced_rate: float
    retry_rate: float
    fallback_rate: float

class SecuritySection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    injection_attempts_count: int
    pii_masked_count: int
    loop_detected_count: int
    language_corrected_count: int

class CostSection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tokens_in_total: int
    tokens_out_total: int
    estimated_usd_per_day: float

class MemorySection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    recall_hit_rate: float
    compactions_count: int

class AgentMetricsConsolidatedResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    period: Literal['7d', '30d', 'all']
    computed_at: datetime
    runs: RunsSection
    tools: ToolsSection
    sourcing: SourcingSection
    security: SecuritySection
    cost: CostSection
    memory: MemorySection
```

## Implémentation note

- Le code se branche dans `backend/app/admin/agent_metrics.py` (existant F56)
  en ajoutant un nouveau handler `agent_metrics_consolidated()` qui :
  - Appelle l'agrégation existante `compute_sourcing_metrics(period)` (F56) pour la section sourcing.
  - Appelle l'agrégation existante `compute_memory_metrics(period)` (F57) pour la section memory.
  - Calcule en local : runs, tools, security, cost via SQL groupés sur `agent_run`/`agent_run_step`/`tool_call_log`.
- L'estimation USD utilise une constante par défaut `LLM_PRICE_PER_1K_TOKENS_USD = 0.004` (configurable via env), retourne 0.0 si compteurs nuls.

## Tests intégration associés

- `tests/integration/admin/test_agent_metrics_consolidated.py` :
  - Seed : 100 `agent_run` + 50 `agent_run_step` avec varying `injection_detected`, `pii_masked_count`, `mode`.
  - Assert : 6 sections présentes, valeurs cohérentes vs SQL direct.
  - Assert : non-admin → 404.
  - Assert : `period=all` agrège sur toute la base ; `period=7d` filtre correctement.
