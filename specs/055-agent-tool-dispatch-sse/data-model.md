# Phase 1 — Data Model: Agent Tool Dispatch & SSE Bridge

Date: 2026-05-06

Cette feature ajoute des **colonnes** à des tables existantes (audit_log + tool_call_log) et introduit des **types runtime Pydantic** ; aucune nouvelle table métier.

## 1 — Extensions DB

### 1.1 — `audit_log` (table existante F04)

Colonnes ajoutées :

| Colonne | Type | Null | FK | Index | Notes |
|---|---|---|---|---|---|
| `tool_call_id` | UUID | YES | tool_call_log(id) | `idx_audit_log_tool_call_id` | Renseigné pour mutations LLM |
| `agent_run_id` | UUID | YES | agent_run(id) | (couvert par join) | Renseigné pour mutations LLM |

Contraintes :
- `tool_call_id IS NOT NULL OR source_of_change != 'llm'` n'est PAS une contrainte applicative (les imports LLM batch peuvent ne pas avoir de tool_call). Validation en service layer.
- Les deux colonnes sont NULLABLE pour préserver la compatibilité avec l'historique.

RLS : héritée de la table existante (`USING (account_id = current_setting('app.current_account_id')::uuid)`).

### 1.2 — `tool_call_log` (table existante F14)

Colonnes ajoutées :

| Colonne | Type | Null | FK | Index | Notes |
|---|---|---|---|---|---|
| `idempotency_key` | TEXT | YES | — | UNIQUE per `(account_id, idempotency_key)` partial index | sha256 32-char tronqué |
| `agent_run_id` | UUID | YES | agent_run(id) | — | Renseigné pour tool calls dispatchés par l'agent |
| `dispatch_result_kind` | TEXT | YES | — | — | Enum `frontend_event \| mutation_result \| tool_message \| error` |

Index UNIQUE partial :
```sql
CREATE UNIQUE INDEX idx_tool_call_log_account_idempotency
  ON tool_call_log (account_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;
```

Status enum étendu pour inclure `cancelled_by_user`, `confirmation_expired`, `rate_limited` (déjà supporté en TEXT NULLABLE — pas de schéma à modifier, validation côté service layer).

### 1.3 — `agent_run.metadata` (colonne JSONB existante F53)

Pas de schéma DB modifié ; usage applicatif :
```json
{
  "pending_confirmations": {
    "<call_id>": {
      "tool_call_id": "<tool_call_log.id UUID>",
      "tool_name": "delete_project",
      "arguments": { ... },
      "expires_at": "2026-05-06T10:30:00Z"
    }
  }
}
```

## 2 — Types runtime Python

### 2.1 — `ToolCategory` enum

```python
class ToolCategory(StrEnum):
    ASK = "ask"          # ask_qcu, ask_qcm, ask_select, ask_number, ask_yes_no, ask_date, ask_file_upload, show_form
    SHOW = "show"        # show_kpi_card, show_radar_chart, ..., show_summary_card
    MUTATION = "mutation" # update_*, create_*, delete_*, generate_*, attach_document, recompute_*, revoke_*
    READ = "read"         # cite_source, search_source, recall_history, flag_unsourced
```

Ajouté en champ obligatoire à `ToolDef` (F14 `tool_registry.py`). Tout tool sans `category` → boot fail-fast.

### 2.2 — `ToolDispatchResult` (Pydantic v2)

```python
class ToolDispatchResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    tool_call_id: str
    tool_name: str
    category: DispatchCategory          # héritée F53 (sse_only|db_mutation|reinvoke_llm) — gardée pour compat
    kind: Literal["frontend_event", "mutation_result", "tool_message", "error"]
    status: Literal["ok", "error", "skipped", "rate_limited", "cancelled_by_user", "confirmation_expired", "pending_confirmation"]

    # Variantes mutuellement exclusives
    output: dict[str, Any] | None = None     # frontend_event payload OR mutation snapshot OR tool_message JSON
    fields_updated: list[str] | None = None  # mutation_result only
    entity_type: str | None = None           # mutation_result only
    entity_id: UUID | None = None            # mutation_result only
    audit_log_id: UUID | None = None         # mutation_result only
    error_summary: str | None = None         # error only
    db_audit_id: UUID | None = None          # back-compat F53 (= audit_log_id)
    is_dry_run: bool = False                 # mode admin

    @model_validator(mode="after")
    def _kind_consistency(self) -> "ToolDispatchResult":
        if self.kind == "mutation_result" and not (self.entity_type and self.entity_id):
            raise ValueError("mutation_result requires entity_type+entity_id")
        if self.kind == "error" and not self.error_summary:
            raise ValueError("error kind requires error_summary")
        return self
```

### 2.3 — `MutationCtx` (frozen dataclass)

```python
from dataclasses import dataclass
from collections.abc import Awaitable, Callable

@dataclass(frozen=True)
class MutationCtx:
    account_id: UUID
    user_id: UUID
    db: Session                      # injectée par le runner
    audit_logger: AuditLogger        # callable wrapper of app.audit.append_diff
    event_bus_publisher: Callable[[UUID, str, dict], Awaitable[None]]
    tool_call_log_id: UUID
    agent_run_id: UUID
    dry_run: bool = False
```

Instancié une fois par tool call. Frozen → impossible à muter, asyncio-safe (NFR-004).

### 2.4 — `MutationResult` (handler return)

```python
class MutationResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    entity_type: str                       # 'Entreprise' | 'Project' | 'Candidature' | ...
    entity_id: UUID
    fields_updated: list[str]              # liste des champs effectivement mis à jour
    snapshot: dict[str, Any] | None = None # snapshot post-update pour le frontend
```

### 2.5 — `RateLimitDecision`

```python
class RateLimitDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')

    allowed: bool
    remaining: int                          # nombre d'appels restants dans la fenêtre
    reset_at: datetime                       # fin de la fenêtre
    reason: Literal["ok", "exceeded", "store_unavailable"]
```

### 2.6 — `PendingConfirmation` (in-memory + JSONB)

```python
class PendingConfirmation(BaseModel):
    model_config = ConfigDict(extra='forbid')

    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    expires_at: datetime
```

## 3 — État partagé `AgentState` (extensions)

Champs ajoutés à `app/agent/state.py` :

| Champ | Type | Description |
|---|---|---|
| `tool_calls_count_in_turn` | int | Compteur incrémenté par dispatch ; cap 10 (FR-015) |
| `dry_run` | bool | Activé par admin via header ou query param |
| `pending_confirmations` | dict[str, PendingConfirmation] | Sync depuis agent_run.metadata au début du tour |

## 4 — Frontend : store Pinia `chat`

Champs ajoutés au store :

| Champ | Type | Notes |
|---|---|---|
| `pendingToolCalls` | `Record<string, ToolCallStatus>` | indexé par `tool_call_id` |
| `pendingViz` | `Record<string, VizPayload[]>` | indexé par `message_id`, rendu inline dans bulle |
| `dryRunActive` | boolean | toggle bandeau |
| `mutationPublishes` | `EntityUpdatePayload[]` | dernières mutations reçues (debug admin) |

`EntityUpdatePayload` :
```typescript
interface EntityUpdatePayload {
  entity_type: string;
  entity_id: string;
  fields_updated: string[];
  source: 'llm';     // toujours 'llm' pour les events F55
}
```

## 5 — Mapping ToolCategory → DispatchCategory

| ToolCategory | DispatchCategory (F53) | Effets |
|---|---|---|
| ASK | SSE_ONLY | tool_invoke → bottom sheet F39 |
| SHOW | SSE_ONLY | tool_invoke → viz inline F40 |
| MUTATION | DB_MUTATION | UPDATE + audit_log + EventBus |
| READ | REINVOKE_LLM | result → ToolMessage → re-run LLM |

## 6 — Migration Alembic (résumé)

Fichier : `backend/alembic/versions/XXXX_f55_audit_tool_call_extensions.py`

Étapes upgrade (cf. research.md §D9). Étapes downgrade : DROP des colonnes/index ajoutés (réversible, AUCUNE perte de données business).

Validation post-migration :
```bash
psql -c "\d+ audit_log" | grep -E 'tool_call_id|agent_run_id'
psql -c "\d+ tool_call_log" | grep -E 'idempotency_key|agent_run_id|dispatch_result_kind'
```

## 7 — Invariants à tester

- `tool_call_log.idempotency_key` UNIQUE per account → test d'intégration `test_dispatch_idempotency_replay.py` insère deux fois la même clé pour deux accounts → no error ; deux fois pour le même account → IntegrityError.
- `audit_log.tool_call_id` réfère bien `tool_call_log.id` → test FK violation rejet INSERT.
- `pending_confirmations` JSONB structure → test `test_dispatch_confirmation_yesno.py` valide via Pydantic.
- ToolDef sans `category` → test `test_boot_fail_fast.py` startup_event raise.
