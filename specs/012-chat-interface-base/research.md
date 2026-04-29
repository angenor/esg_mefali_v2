# Phase 0 — Research: F13 Chat Interface Base

## Decisions

### D1. Streaming transport for assistant messages
- **Decision**: Server-Sent Events (`Content-Type: text/event-stream`).
- **Rationale**: stack already uses SSE for `/me/events`; reusing keeps single transport, browser native `EventSource`, simpler firewall traversal vs WebSocket.
- **Alternatives**: WebSocket (extra infra), chunked HTTP NDJSON (no native EventSource).

### D2. SSE event envelope format
- **Decision**: each event = `event: <type>\ndata: <json>\n\n`. Allowed types in F13: `text_delta`, `tool_call_started`, `tool_call_completed`, `message_done`, `error`.
- **Rationale**: typed self-describing; F14+ can extend without breaking F13 clients.

### D3. Title generation strategy
- **Decision**: server default `Conversation du DD/MM/YYYY` at thread creation (UTC fallback).
- **Rationale**: deterministic, testable. LLM retitling postponed.

### D4. `/me/events` SSE infrastructure
- **Decision**: in-process asyncio publisher/subscriber. Singleton `EventBus` keyed by `account_id` holding `asyncio.Queue` per active connection.
- **Rationale**: MVP single FastAPI process; no Redis/Celery dep. Migrating to Postgres LISTEN/NOTIFY straightforward later.

### D5. Embedding compute
- **Decision**: FastAPI `BackgroundTasks` after the response is returned. Voyage AI failures swallowed and logged; `embedding` stays NULL.
- **Rationale**: spec mandates non-blocking; no queue infra exists yet.

### D6. Stream chunk persistence
- **Decision**: chunks NOT persisted; only the consolidated final assistant message is inserted into `chat_message` once `message_done` is reached.
- **Rationale**: spec edge case explicit.

### D7. LLM availability and CI fallback
- **Decision**: when `LLM_API_KEY` missing/invalid (or `LLM_STUB=1`), the streaming generator emits a deterministic stub envelope sequence (`text_delta` `[F13 stub: LLM non configuré]`, then `message_done`).
- **Rationale**: allows CI/dev without secret rotation.

### D8. Body size limits
- **Decision**: enforced via Pydantic `max_length` (32 KB content, 64 KB payload). Total body > 128 KB → 413 (FastAPI/middleware).
- **Rationale**: testable, fails fast.

### D9. Archived-thread send semantics
- **Decision**: 409 with `{detail: "thread_archived"}`.
- **Rationale**: explicit, no implicit unarchive, audit-friendly.

### D10. `context_json` whitelist
- **Decision**: dedicated Pydantic model with `model_config = ConfigDict(extra='forbid')` and exactly four optional fields: `page` (str), `entity_type` (str|None), `entity_id` (str|None), `selection` (str|None).
- **Rationale**: security + input-validation discipline.

## Open questions

None. No `NEEDS CLARIFICATION` remaining.

## Library notes

- `sse-starlette` preferred for `EventSourceResponse`; fallback to `StreamingResponse(media_type="text/event-stream")` if dep absent.
- `openai` SDK: `client.chat.completions.create(stream=True)` yields chunks mappable to envelope events.
- Voyage client at `backend/app/embeddings_client.py`.
