# Implementation Plan: Chat Interface Base (F13)

**Branch**: `012-chat-interface-base` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification at `specs/012-chat-interface-base/spec.md`

## Summary

Deliver the conversational shell on which all subsequent LLM features (F14–F18) plug. Backend: `chat_thread` table (new), `chat_message` enriched (`thread_id`, `context_json`, role CHECK), REST endpoints under `/me/chat/threads`, SSE streaming for assistant responses (typed JSON envelope), SSE `/me/events` for cross-section realtime entity updates (in-process asyncio fan-out, account-scoped). Voyage AI embedding computed in `BackgroundTasks` post-turn, NULL on failure. Multi-tenant RLS strict; audit-log entry on every thread create/archive and message persistence. Frontend Nuxt component is **DEFERRED** (per orchestration brief) — backend ships REST + SSE only.

## Technical Context

**Language/Version**: Python 3.11+ (backend), Nuxt 4 (frontend, deferred for F13).
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x async, Pydantic v2 (`extra='forbid'`), Alembic, pgvector, openai SDK (OpenRouter), Voyage AI client (`embeddings_client.py`), `sse-starlette` (or stdlib `StreamingResponse`).
**Storage**: PostgreSQL 16 + pgvector. RLS enforced via `app.current_account_id`.
**Testing**: pytest + httpx AsyncClient, sqlalchemy async, transactional fixtures from `backend/conftest.py`.
**Target Platform**: Linux server (FastAPI ASGI), single process MVP.
**Project Type**: Web service (REST + SSE) + Nuxt SPA (frontend deferred).
**Performance Goals**: First-token < 1.5 s typical (SC-003); echo < 100 ms (NFR-002); roundtrip "hello" < 3 s (SC-001).
**Constraints**: No Redis/Celery added. RLS strict. Body limits: content ≤ 32 KB, payload_json ≤ 64 KB, total ≤ 128 KB.
**Scale/Scope**: MVP single FastAPI process; threads/messages bounded by user activity.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.
Mark each gate as ✅ pass / ⚠ deferred / ❌ violated. Any ❌ on a NON
NEGOTIABLE principle blocks the plan and requires either redesign or a
constitutional amendment — never a workaround in `Complexity Tracking`.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F13 ne crée aucune entité catalogue/ESG. La réponse LLM est conversationnelle, sans assertion factuelle (les tools sourcés viendront en F14+). | ✅ N/A |
| P2 | Multi-tenant RLS | `chat_thread` et `chat_message` ont `account_id` + RLS `USING (account_id = current_setting('app.current_account_id')::uuid)`. SSE filtre server-side. Cross-tenant → 404. | ✅ |
| P3 | Audit log append-only | Création/archive thread + persistance message émettent une entrée `audit_log` avec `source_of_change ∈ {manual, llm}`. | ✅ |
| P4 | Versioning + snapshot | F13 ne touche pas aux référentiels ni aux candidatures. | ✅ N/A |
| P5 | Money typé | Aucune valeur monétaire manipulée. | ✅ N/A |
| P6 | Pivot Indicateur unique | Aucune donnée ESG persistée. | ✅ N/A |
| P7 | Plateforme fermée intermédiaires | Pas de nouveau rôle ; chat reste PME-only via auth existant. | ✅ |
| P8 | Édition manuelle + sync LLM | `/me/events` SSE est précisément le mécanisme qui permettra la sync LLM→UI dès F17. Pas de champ LLM-only ici. | ✅ |
| P9 | Tool-use LLM fiable | F13 n'expose AUCUN tool LLM (différé F14/F15/F17). Le streaming envelope prépare l'extension typée. | ✅ N/A |
| P10 | UX bottom sheet | Frontend différé. Le contrat backend (REST/SSE) ne pré-empte pas le bottom sheet ; FR-015 garantit le slot input séparé. | ✅ |

**Verdict (initial)** : tous les gates passent. Aucun écart à justifier.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via
  OpenRouter (interchangeable par env) ; embeddings Voyage `voyage-3.5`
  (1024 dim).
- Dev local : backend en `.venv`, Postgres seul service dockerisé,
  frontend en `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement
  (jamais USA).
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 dès le MVP.
- Langue : français par défaut ; anglais uniquement pour dossiers vers
  offres `accepted_languages = 'en'`.

## Phase 0 — Research

See [`research.md`](./research.md). Decisions résumées :

1. Streaming transport = SSE (single transport, simpler client).
2. Event envelope = typed JSON `{type, data}` ; types : `text_delta | tool_call_started | tool_call_completed | message_done | error`.
3. Title strategy = server default `Conversation du DD/MM/YYYY`. LLM retitling deferred.
4. `/me/events` infra = in-process asyncio per-account fan-out (singleton `EventBus`). Postgres LISTEN/NOTIFY différé.
5. Embedding = FastAPI `BackgroundTasks` non-blocking ; failure → row valid avec `embedding=NULL`.
6. Stream chunk persistence = consolidated final message only.
7. LLM availability = real `minimax-m2.7` via OpenRouter quand `LLM_API_KEY` configuré ; sinon stub déterministe `[F13 stub: LLM non configuré]`.
8. Body limits enforced via Pydantic `max_length` ; overflow → 413.
9. Archived thread send → 409 `thread_archived`.
10. `context_json` whitelist via Pydantic `extra='forbid'` → 422 sur extra fields.

## Phase 1 — Design & Contracts

### Data model (`data-model.md`)

- `chat_thread` (NEW) : `id UUID PK`, `account_id UUID NOT NULL FK account(id)`, `user_id UUID NULL FK account_user(id)`, `title TEXT NOT NULL`, `archived BOOLEAN NOT NULL DEFAULT false`, `created_at`, `updated_at`, `version`, `deleted_at`. Index `(account_id, user_id, archived, updated_at DESC)`. RLS policy.
- `chat_message` (ALTER) : ajout `thread_id UUID NULL FK chat_thread(id) ON DELETE CASCADE`, `context_json JSONB NULL`. CHECK `role IN ('user','assistant','system','tool')`. Lignes legacy → `thread_id NULL` accepté.
- RLS activée + forcée sur les deux tables.

Voir [`data-model.md`](./data-model.md).

### Contracts (`contracts/`)

- `contracts/chat-threads.openapi.yaml` — `GET/POST /me/chat/threads`, `DELETE /me/chat/threads/{id}`, `GET /me/chat/threads/{id}/messages`, `POST /me/chat/threads/{id}/messages` (SSE).
- `contracts/me-events.openapi.yaml` — `GET /me/events` SSE pour `entity_updated`.
- `contracts/sse-envelope.schema.json` — JSON-Schema typé.

### Quickstart (`quickstart.md`)

Test e2e manuel : migrer, login PME, créer thread, envoyer message + observer SSE deltas, lire messages, déclencher event_bus → second client reçoit, archive thread → 409 sur post.

Voir [`quickstart.md`](./quickstart.md).

### Agent context

`CLAUDE.md` pointe déjà vers le plan via les marqueurs SPECKIT.

## Phase 2 — Task generation strategy (entrée de `/speckit-tasks`)

Ordre logique :
1. Foundational : migration Alembic 0011, modèles SQLAlchemy, schémas Pydantic, EventBus singleton, config.
2. US1/US6 : REST CRUD threads (list, create, archive).
3. US2 + FR-023 : persistance messages + lazy thread create.
4. US3 + FR-007/FR-025 : whitelist `context_json`.
5. US4 + FR-005/FR-027 : SSE `/me/events` (asyncio fan-out).
6. NFR-003 + FR-006/FR-024 : streaming SSE assistant + LLM stub fallback.
7. FR-008/FR-026 : Voyage embedding background task.
8. FR-010 : audit log entries.
9. RLS regression tests (P2).
10. Frontend Nuxt → **[DEFERRED]** par instruction d'orchestration.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/0011_f13_chat_thread_and_message_enrich.py
├── app/
│   ├── chat/
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy ChatThread (chat_message déjà existant ailleurs)
│   │   ├── schemas.py           # Pydantic ContextJson, ChatThread*, ChatMessage*, SSE envelopes
│   │   ├── repository.py        # CRUD threads + messages
│   │   ├── service.py            # business logic: lazy create, archive guard, persist turn
│   │   ├── llm_stream.py         # SSE generator + LLM call (stub fallback)
│   │   ├── event_bus.py          # in-process asyncio per-account fan-out
│   │   ├── embedding_task.py     # BackgroundTasks helper for Voyage
│   │   └── api.py                # FastAPI router /me/chat/* and /me/events
│   └── main.py                  # mount router
└── tests/
    └── chat/
        ├── test_threads_crud.py
        ├── test_messages_persistence.py
        ├── test_context_whitelist.py
        ├── test_sse_assistant_stream.py
        ├── test_event_bus.py
        ├── test_me_events_sse.py
        ├── test_embedding_background.py
        ├── test_audit_log.py
        └── test_rls_isolation.py
```

**Structure Decision**: option « web app backend » ; le frontend Nuxt est différé pour F13 (livraison F15+).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _aucune_ | — | — |
