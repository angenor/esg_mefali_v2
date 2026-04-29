---
description: "Task list — F13 Chat Interface Base"
---

# Tasks: F13 Chat Interface Base

**Input**: `/specs/012-chat-interface-base/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: parallelizable.
- **[Story]**: US1..US8 (spec.md).
- TDD: tests first (RED), then implementation (GREEN).

## Phase 1 — Setup

- [ ] T001 Create backend module skeleton at `backend/app/chat/__init__.py` and add empty `models.py`, `schemas.py`, `repository.py`, `service.py`, `event_bus.py`, `embedding_task.py`, `llm_stream.py`, `api.py`.
- [ ] T002 [P] Create test package skeleton `backend/tests/chat/__init__.py` and shared fixtures file `backend/tests/chat/conftest.py` (two-tenant fixtures A and B).

## Phase 2 — Foundational (blocking)

- [ ] T003 Write Alembic migration `backend/alembic/versions/0011_f13_chat_thread_and_message_enrich.py` per data-model.md (chat_thread table, ALTER chat_message add thread_id+context_json+role CHECK, indexes, RLS enable+force, down-revision = 0010_f11_entreprise_enrich).
- [ ] T004 [P] Add SQLAlchemy `ChatThread` model in `backend/app/chat/models.py`.
- [ ] T005 [P] Define Pydantic schemas in `backend/app/chat/schemas.py` (`ContextJsonModel(extra='forbid')`, `PostMessageBody` with `content max_length=32768`, `payload_json` size validator ≤ 64 KB serialized, SSE envelope discriminated model).
- [ ] T006 [P] Implement `EventBus` singleton in `backend/app/chat/event_bus.py` (asyncio per-account fan-out: `subscribe(account_id)`, `publish(account_id, event)`, clean unsubscribe on cancel).
- [ ] T007 [P] Implement embedding background helper in `backend/app/chat/embedding_task.py` (Voyage AI call, NULL on failure).
- [ ] T008 [P] Implement repository in `backend/app/chat/repository.py` (`list_threads`, `create_thread`, `archive_thread`, `get_thread_by_id`, `list_messages_by_thread`, `insert_message`).
- [ ] T009 [P] Implement service in `backend/app/chat/service.py` (`ensure_active_thread`, `archive_thread`, `persist_user_turn`, `persist_assistant_turn`, audit_log emission with `source_of_change ∈ {manual, llm}`).
- [ ] T010 Implement `backend/app/chat/llm_stream.py` (async generator: OpenRouter streaming when `LLM_API_KEY` set; deterministic stub `[F13 stub: LLM non configuré]` otherwise; emits typed envelope events).
- [ ] T011 Wire FastAPI router in `backend/app/chat/api.py` and mount in `backend/app/main.py` (auth dependency sets `app.current_account_id`).

## Phase 3 — US1 Floating chat / threads CRUD (P1)

- [ ] T012 [US1] RED test `backend/tests/chat/test_threads_crud.py::test_list_threads_empty_then_after_create`.
- [ ] T013 [US1] RED test `backend/tests/chat/test_threads_crud.py::test_default_title_format` (Conversation du DD/MM/YYYY).
- [ ] T014 [US1] GREEN — implement `GET /me/chat/threads` and `POST /me/chat/threads` in `backend/app/chat/api.py`.
- [ ] T015 [US1] RED + GREEN test `backend/tests/chat/test_threads_crud.py::test_archive_thread_204_and_audit_row`.
- [ ] T016 [US1] [P] RED + GREEN test `backend/tests/chat/test_rls_isolation.py::test_threads_cross_tenant_404`.

## Phase 4 — US2 Persistent history (P1)

- [ ] T017 [US2] RED test `backend/tests/chat/test_messages_persistence.py::test_send_message_persists_user_and_assistant`.
- [ ] T018 [US2] RED test `backend/tests/chat/test_messages_persistence.py::test_lazy_thread_create_via_post_threads_when_none_active`.
- [ ] T019 [US2] RED test `backend/tests/chat/test_messages_persistence.py::test_get_messages_paginated_after_id`.
- [ ] T020 [US2] GREEN — implement `GET /me/chat/threads/{id}/messages` and persistence path in `POST /me/chat/threads/{id}/messages` (user message saved before SSE; assistant final consolidated row inserted on `message_done`).
- [ ] T021 [US2] RED + GREEN test `backend/tests/chat/test_messages_persistence.py::test_post_to_archived_thread_returns_409`.
- [ ] T022 [US2] RED + GREEN test `backend/tests/chat/test_messages_persistence.py::test_oversized_content_returns_413_or_422`.

## Phase 5 — US3 context_json whitelist (P1)

- [ ] T023 [US3] RED test `backend/tests/chat/test_context_whitelist.py::test_extra_field_returns_422`.
- [ ] T024 [US3] RED test `backend/tests/chat/test_context_whitelist.py::test_context_persisted_verbatim_on_user_row`.
- [ ] T025 [US3] GREEN — wire `ContextJsonModel(extra='forbid')` validation; persist `context_json` on the user row only.

## Phase 6 — US4 /me/events SSE (P1)

- [ ] T026 [US4] RED test `backend/tests/chat/test_event_bus.py::test_publish_then_subscribe_receives_event`.
- [ ] T027 [US4] RED test `backend/tests/chat/test_event_bus.py::test_cross_tenant_isolation` (publish on A, subscribe as B → no event).
- [ ] T028 [US4] [P] RED test `backend/tests/chat/test_me_events_sse.py::test_sse_endpoint_streams_publishes`.
- [ ] T029 [US4] GREEN — implement `GET /me/events` SSE handler in `backend/app/chat/api.py`.

## Phase 7 — US5 Streaming assistant (P1)

- [ ] T030 [US5] RED test `backend/tests/chat/test_sse_assistant_stream.py::test_stub_mode_emits_text_delta_then_message_done`.
- [ ] T031 [US5] RED test `backend/tests/chat/test_sse_assistant_stream.py::test_stream_consolidates_final_message_in_db`.
- [ ] T032 [US5] GREEN — finalize `backend/app/chat/llm_stream.py` and wire it into `POST messages` (`text/event-stream` content-type).

## Phase 8 — Embedding background + Audit log (P1)

- [ ] T033 [P] RED test `backend/tests/chat/test_embedding_background.py::test_embedding_filled_in_background` (monkeypatch embeddings_client).
- [ ] T034 [P] RED test `backend/tests/chat/test_embedding_background.py::test_embedding_failure_leaves_null_and_does_not_raise`.
- [ ] T035 GREEN — wire `BackgroundTasks` in `POST messages` after assistant persistence.
- [ ] T036 [P] RED + GREEN test `backend/tests/chat/test_audit_log.py::test_thread_create_and_message_insert_emit_audit` (covers thread create/archive + user/assistant message insert with correct source_of_change).

## Phase 9 — US6 Threads ordering (P2)

- [ ] T037 [US6] RED + GREEN test `backend/tests/chat/test_threads_crud.py::test_list_orders_by_updated_at_desc_and_excludes_archived`.

## Phase 10 — US7 Loading indicator (P2) [DEFERRED]

- [ ] T038 [US7] [DEFERRED] Frontend typing indicator — covered when F15 lands the Nuxt shell.

## Phase 11 — US8 Clickable entity links (P3) [DEFERRED]

- [ ] T039 [US8] [DEFERRED] Frontend message renderer link parsing — F15+ frontend work.

## Phase 12 — Frontend Nuxt chat shell [DEFERRED]

- [ ] T040 [DEFERRED] `<ChatFloating>`, `useChatContext()`, `<ChatMessageRenderer>` in `frontend/app/components/chat/` — DEFERRED per orchestration brief; F13 ships backend only.

## Phase 13 — Polish

- [ ] T041 Run `ruff check backend/app/chat backend/tests/chat` — fix any lint issues.
- [ ] T042 Coverage gate: `pytest --cov=app/chat --cov-fail-under=80 backend/tests/chat`.
- [ ] T043 Update `.cc-runtime/logs/manual-tests-13.md` from quickstart.md.

## Dependencies

- Phase 1 → Phase 2 → Phases 3–8.
- Phase 9 depends on Phase 3.
- Phases 10–12 are DEFERRED.
- Phase 13 last.

## MVP scope

Phases 1, 2, 3, 4, 5, 6, 7, 8 = full backend MVP for F13.
