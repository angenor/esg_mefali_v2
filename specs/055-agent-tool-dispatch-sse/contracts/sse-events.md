# SSE Events Contract — F55

Date: 2026-05-06

Contrat des frames SSE exposés par `POST /api/chat/stream` (F53 endpoint, enrichi par F55). Frontend consumer : `frontend/app/composables/useChatStream.ts`.

## Format générique

Chaque frame respecte la spec EventSource :
```
event: <event_type>
data: <json_payload>
id: <optional_event_id>

```
(double newline en fin de frame).

Lorsque le mode admin `dry_run=True` est actif, chaque `event_type` est préfixé `dry_run:` (ex. `dry_run:mutation`).

## Inventaire des events

### `text_delta`

Push de tokens partiels du LLM en cours de streaming.

```json
{
  "delta": "string",
  "message_id": "uuid"
}
```

Source : LangChain `on_chat_model_stream`. Frontend → append au `content` du message assistant en cours.

### `tool_call_started`

Debug only. Émis par LangChain `on_tool_start`. Frontend ignore par défaut (option `showDebugEvents`).

```json
{
  "tool_call_id": "string",
  "tool_name": "string"
}
```

### `tool_invoke`

Émis par le dispatcher pour ASK et SHOW. Frontend → bottom sheet F39 (ASK) ou viz inline F40 (SHOW).

```json
{
  "tool_call_id": "string",
  "tool_name": "string",
  "category": "ASK | SHOW",
  "arguments": { /* validated payload */ },
  "message_id": "uuid"
}
```

### `mutation`

Émis après une mutation DB réussie. Frontend → `useChatEventBus().emit('entity_updated', ...)` → stores Pinia refresh.

```json
{
  "tool_call_id": "string",
  "tool_name": "string",
  "entity_type": "Entreprise | Project | Candidature | ...",
  "entity_id": "uuid",
  "fields_updated": ["string"],
  "audit_log_id": "uuid",
  "snapshot": { /* post-mutation entity snapshot */ },
  "message_id": "uuid"
}
```

### `tool_call_completed`

**Admin only**. Indicateur fin de tool dispatch (succès). Frontend filtre par `userRole==='admin'`.

```json
{
  "tool_call_id": "string",
  "tool_name": "string",
  "kind": "frontend_event | mutation_result | tool_message | error",
  "status": "ok | error | rate_limited | cancelled_by_user | confirmation_expired",
  "duration_ms": 42
}
```

### `validation_retry`

Émis quand la validation Pydantic d'un tool call échoue et qu'un retry est lancé (limite 2, P9).

```json
{
  "retry_count": 1,
  "tool_name": "string",
  "error_summary": "string (truncated 500 chars)"
}
```

### `error`

Émis sur erreur non récupérable (retry exhausted, handler exception, rate limit dépassé sans fallback, RLS refus).

```json
{
  "code": "rate_limited | dispatch_error | validation_exhausted | rls_refused | ...",
  "message": "string (user-safe)",
  "agent_run_id": "uuid | null"
}
```

### `message_done`

Fin du graph LangGraph. Frontend → finaliser le message assistant.

```json
{
  "message_id": "uuid",
  "agent_run_id": "uuid",
  "tokens_used": { "in": 1234, "out": 567 },
  "final_text": "string"
}
```

## Ordre des events

Pour un tour LLM typique avec 1 tool ASK :
```
1. text_delta (×N)
2. tool_call_started
3. tool_invoke (ASK)
4. tool_call_completed (admin only)
5. message_done
```

Pour un tour avec 1 tool MUTATION :
```
1. text_delta (×N)
2. tool_call_started
3. mutation
4. tool_call_completed (admin only)
5. message_done
```

Pour un tour avec READ + reinjection :
```
1. text_delta (×N)
2. tool_call_started
3. (tool_message ré-injecté en interne, pas d'event SSE direct)
4. text_delta (×N) — 2e LLM run après réinjection
5. message_done
```

Pour un tour avec mutation destructive (delete_*) :
```
1. text_delta (×N)
2. tool_invoke (ASK pour ask_yes_no de confirmation)
3. message_done
(tour suivant, après réponse user "Oui")
4. text_delta (×N)
5. mutation (le call original ré-exécuté)
6. message_done
```

## Resilience reconnect

Si le frontend perd la connexion SSE et reconnecte avec `Last-Event-ID: <id>`, le backend rejoue les events depuis cet `id`. L'idempotence DB-backed garantit qu'aucune mutation n'est ré-exécutée (FR-011).

## Rate limit & fail-safe

Sur dépassement rate limit ou store inaccessible, le dispatcher émet :
- `error` (code `rate_limited` ou `rate_limit_unavailable`)
- `tool_call_completed` (admin only, `status='rate_limited'` ou `error`)
- `message_done` (avec `final_text` fallback poli)

Aucun `mutation` ni `tool_invoke` n'est émis.
