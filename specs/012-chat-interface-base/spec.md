# Feature Specification: Chat Interface Base (Floating Chat + Page Context + Realtime Sync)

**Feature Branch**: `012-chat-interface-base`
**Created**: 2026-04-29
**Status**: Draft
**Input**: F13 — Interface Chat Multimodale & Contexte de Page (docs_et_brouillons/features/13-chat-interface-base.md)

## Clarifications

### Session 2026-04-29

- Q: Streaming transport for assistant messages? → A: SSE (single transport reused for `/me/events`).
- Q: Event envelope shape? → A: typed JSON `{type, data}` with `text_delta | tool_call_started | tool_call_completed | message_done | error`.
- Q: Posting a message into an archived thread? → A: HTTP 409 `thread_archived`, no implicit unarchive.
- Q: Max message size? → A: `content` ≤ 32 KB, `payload_json` ≤ 64 KB, total body ≤ 128 KB → 413 on overflow.
- Q: First-thread creation timing? → A: Lazy — create on first message if no active thread exists; explicit `POST /threads` still available.
- Q: LLM availability in CI? → A: real `minimax-m2.7` via OpenRouter when configured; fallback text `[F13 stub: LLM non configuré]` otherwise.
- Q: `context_json` extra fields? → A: reject 422; whitelist = `{page, entity_type, entity_id, selection}`.
- Q: Embedding compute timing? → A: FastAPI BackgroundTasks, non-blocking, NULL on failure.
- Q: `/me/events` infrastructure? → A: in-process asyncio per-account fan-out (singleton EventBus). Postgres LISTEN/NOTIFY deferred.
- Q: Stream-chunk persistence? → A: final consolidated assistant message only; chunks not stored.
- Q: Frontend chat-floating component? → A: DEFERRED to a later micro-PR; F13 ships backend only (REST + SSE), per orchestration note.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Floating chat available on every page (Priority: P1)

A PME user wants a floating chat button (bottom-right) accessible from every authenticated page. Opening the button shows a persistent conversation window above the page content. Closing/opening state survives navigation; conversation history is preserved across navigations and sessions.

**Why this priority**: The chat is the primary entry point of the platform. Without it, the rest of the LLM features (F14-F18) have nowhere to live.

**Independent Test**: Authenticate as a PME, open the chat on `/`, send a message; navigate to `/profil/entreprise` then `/profil/projets/{id}`; on each page, the chat button is present, the chat window can be reopened, the messages are still there, and its open/closed state persists per the user's last action.

**Acceptance Scenarios**:

1. **Given** a logged-in PME on any authenticated page, **When** they click the floating button, **Then** the chat window opens above the page content without blocking page navigation, and previous messages (if any) are loaded.
2. **Given** the chat window is open and the user navigates to another page, **When** the new page is rendered, **Then** the chat remains open with the same thread and the scroll position is preserved at the bottom.
3. **Given** the user closes the chat, **When** they reload the application or navigate, **Then** the chat reopens in the same closed state (UI state persisted locally).

---

### User Story 2 - Persistent conversation history (Priority: P1)

A PME wants every exchange with the LLM saved in the database and reloadable when they sign in again. They can also start a fresh conversation while keeping access to the older one.

**Why this priority**: Without persistence, no continuity, no memory, no audit. F18 (RAG/memory) cannot operate without this.

**Independent Test**: Send 3 messages in session A, log out, log back in, the same thread is reopened with all 3 messages. Click "New conversation" and the previous thread remains in the threads list (archived/old) and a new empty thread starts.

**Acceptance Scenarios**:

1. **Given** a PME has never used the chat, **When** they open it for the first time, **Then** an empty thread is automatically created and shown.
2. **Given** a PME has an existing active thread, **When** they sign in again, **Then** that thread is loaded with messages in chronological order, scroll at the bottom.
3. **Given** the user clicks "New conversation", **When** confirmed, **Then** a new empty thread becomes the active thread and the previous thread remains accessible from the threads list.
4. **Given** a thread exists with messages, **When** the user deletes (archives) it, **Then** it disappears from the active list but messages remain in the database (audit trail), and a new empty thread becomes active if it was the last one.

---

### User Story 3 - LLM knows the current page (Priority: P1)

When a PME is on `/profil/projets/{id}` and types "add an impact indicator", the system implicitly understands that "this project" refers to the currently displayed project. Page context is sent with every message.

**Why this priority**: Without contextual binding the chat would force users to repeat IDs and resource names — defeating the conversational-first UX.

**Independent Test**: Send a message from page `/profil/projets/abc-123`. Inspect the persisted message in the database — its `context_json` MUST contain `{ "page": "/profil/projets/abc-123", "entity_type": "projet", "entity_id": "abc-123" }`. F13 only stores it; downstream features (F14/F18) consume it.

**Acceptance Scenarios**:

1. **Given** a PME is on a page that maps to an entity, **When** they send a message, **Then** the request body includes a `context_json` with the page path, entity type, entity id and optional selection.
2. **Given** the page does not map to a specific entity (e.g. dashboard root), **When** the user sends a message, **Then** the `context_json` still contains the page path with `entity_type=null` and `entity_id=null`.
3. **Given** the page contains a sensitive value (token, secret, password), **When** the message is sent, **Then** that sensitive field is NOT included in `context_json` (whitelist-only fields).

---

### User Story 4 - Realtime UI sync when an entity changes (Priority: P1)

When the LLM (or any backend mutation) modifies a domain entity that the user is currently viewing, the UI must reflect the change without a page reload.

**Why this priority**: Conversational mutations (F17) are useless if the user must refresh to see the result.

**Independent Test**: Open the company profile page. From a backend test fixture, fire an `entity_updated` event for the user's `entreprise` entity. The dedicated page section subscribes to the event stream and reloads the relevant data within 2 seconds.

**Acceptance Scenarios**:

1. **Given** a PME is viewing a page bound to an entity, **When** the backend emits an `entity_updated` event for that entity, **Then** the page section reloads its data automatically within 2 seconds.
2. **Given** another tenant emits an event, **When** the current user is connected, **Then** the user does NOT receive the other tenant's event (multi-tenant isolation).
3. **Given** the user closes the page, **When** events continue to be emitted, **Then** the client unsubscribes cleanly (no leaked connection).

---

### User Story 5 - Bubble vs input zone separation (Priority: P1)

Conversation bubbles (LLM and user messages) appear in the upper area; the input area is at the bottom. The input area can switch between free-text input and a bottom-sheet response component (delivered by F15). Interactive components are NEVER rendered inline inside an LLM bubble.

**Why this priority**: This is a hard UX invariant of the platform (Module 0). Violating it leaks form widgets into the conversation history and breaks the bottom-sheet-only rule.

**Independent Test**: Send several text messages. The bubbles render content as text only. The input area is always at the bottom and never inside a bubble. A `<slot>` exists in the input area to host future bottom-sheet response widgets (F15) without modifying F13 components.

**Acceptance Scenarios**:

1. **Given** a conversation with mixed user and assistant messages, **When** rendered, **Then** every message is in a bubble in the upper conversation zone and no interactive form control is visible inside any bubble.
2. **Given** the input zone, **When** the assistant emits a structured response request (future F15), **Then** the renderer slot in the input zone is the only place that can host interactive widgets.

---

### User Story 6 - Threads list and navigation (Priority: P2)

A PME can list all their conversation threads, switch between them, and archive any of them. Threads have an auto-generated title (default `Conversation du DD/MM/YYYY`).

**Acceptance Scenarios**:

1. **Given** several threads exist, **When** the user opens the threads panel, **Then** all non-archived threads are listed by `updated_at` desc.
2. **Given** the user clicks a thread, **When** it loads, **Then** that thread becomes active and its messages are loaded.
3. **Given** the user archives a thread, **When** confirmed, **Then** the thread disappears from the active list but its messages are not deleted from the database.

---

### User Story 7 - Loading indicator and animations (Priority: P2)

A PME can clearly see when the LLM is processing (animated `…` indicator) and when long actions are running (progress bar/streaming).

**Acceptance Scenarios**:

1. **Given** the user sent a message, **When** the assistant is generating the response, **Then** an animated typing indicator is shown.
2. **Given** the assistant is streaming a response, **When** tokens arrive, **Then** they appear progressively in the bubble.

---

### User Story 8 - Clickable links between conversation and UI (Priority: P3)

When the assistant mentions an entity ("votre projet panneaux solaires"), the message contains a clickable link that navigates to the entity's page.

**Acceptance Scenarios**:

1. **Given** an assistant message containing an entity reference, **When** the user clicks it, **Then** the application navigates to the entity's canonical page.

---

### Edge Cases

- Browser refresh during streaming: the client reconnects and the partial message either resumes or is finalized as a complete message on next load (no half-baked bubble persists).
- Two tabs of the same user: messages and `entity_updated` events fan-out to all tabs of the same account.
- Mobile virtual keyboard: the chat window uses dynamic viewport units so the keyboard does not crop the input.
- Very large `payload_json` (>100 KB): F13 stores it as-is for MVP; clients must not crash if missing/oversized fields.
- User from tenant A must NEVER receive any event or message from tenant B (RLS strict).
- Token-level streaming chunks must not be persisted as separate rows; only the consolidated final assistant message is persisted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist conversation threads with `id`, `account_id`, `user_id`, `title`, `created_at`, `updated_at`, `archived` flag.
- **FR-002**: System MUST persist conversation messages with `id`, `thread_id`, `role` (user/assistant/system/tool), `content`, optional `payload_json`, optional `embedding` vector, optional `context_json`, `created_at`. Messages MUST be linked to a thread that belongs to the same account as the message.
- **FR-003**: System MUST expose authenticated REST endpoints to:
  - List the current user's non-archived threads (newest first).
  - Create a new thread (defaults title `Conversation du DD/MM/YYYY`).
  - List paginated messages of a given thread (with `after_id` cursor).
  - Send a new user message to a thread and receive assistant message(s).
  - Archive (soft-delete) a thread.
- **FR-004**: The send-message endpoint MUST accept `{ content, payload_json?, context_json }` and return `{ messages: [...] }`. The thread's `updated_at` MUST be refreshed.
- **FR-005**: System MUST expose a Server-Sent Events stream that delivers, for the current authenticated user, events of type `entity_updated` filtered by the user's `account_id`. Cross-tenant leakage MUST be impossible (server-side filtering, not client-side).
- **FR-006**: The streaming format for assistant responses MUST use a typed JSON envelope with at least the events `text_delta`, `tool_call_started`, `tool_call_completed`, `message_done`. Each event MUST be self-describing (type field) so future tools (F15/F16/F17) can extend it without breaking F13 clients.
- **FR-007**: System MUST send a `context_json` with every user message containing only whitelisted fields: `page` (string), `entity_type` (string|null), `entity_id` (string|null), `selection` (string|null). The whitelist MUST be enforced server-side; unknown fields MUST be rejected or stripped.
- **FR-008**: System MUST compute and store an embedding (Voyage AI, 1024 dims) for every persisted message AFTER the turn completes. Embedding failure MUST NOT block the user-visible response; it can be retried asynchronously.
- **FR-009**: System MUST enforce row-level multi-tenant isolation (RLS) on `chat_thread` and `chat_message` so that no query can return rows belonging to a different `account_id` regardless of caller logic.
- **FR-010**: Every state change on threads (create, archive) and message persistence MUST emit an entry in the audit log (append-only, F04) with `account_id`, `user_id`, action, target id.
- **FR-011**: System MUST never expose system prompts, API keys, or internal secrets to the client. Assistant messages with `role=system` MUST NOT be returned through the public read endpoints.
- **FR-012**: A floating chat shell MUST be present on every authenticated page; its open/closed/compact state MUST persist locally per user.
- **FR-013**: The frontend MUST expose a composable that returns the current page context object, derived from the route plus an optional in-page registration (e.g. project page registers `entity_id`).
- **FR-014**: The message rendering component MUST switch on `payload_json.type` so future feature deliveries (F15 response tools, F16 visualization tools, F17 mutation tools) can register renderers without modifying F13 code.
- **FR-015**: The input area MUST contain a slot reserved for bottom-sheet response widgets (F15 will fill it). F13 ships the slot empty (free-text input only).
- **FR-016**: The chat MUST be accessible: focus trap when open, ESC closes it, ARIA `dialog` on the window, ARIA `log` on the messages list, keyboard-reachable send.
- **FR-017**: User-visible echo of a sent message MUST appear in the conversation within 100 ms (optimistic update before server acknowledgement).
- **FR-018**: Streaming assistant tokens MUST appear progressively in the bubble (no buffering until final message).
- **FR-019**: System MUST tolerate `embedding` column being NULL (legacy or asynchronous fill) and continue to render the message normally.
- **FR-020**: Title auto-generation: a fresh thread MUST receive a default title `Conversation du DD/MM/YYYY` (server-side, server-localized to the user's timezone or UTC fallback). LLM-driven retitling is OUT OF SCOPE for F13.
- **FR-021**: Posting a message to an archived thread MUST return HTTP 409 with error code `thread_archived`. No implicit unarchive.
- **FR-022**: Request body limits — `content` ≤ 32 KB, `payload_json` ≤ 64 KB, total body ≤ 128 KB. Overflow MUST return HTTP 413.
- **FR-023**: First-thread creation is lazy: if a PME has no active (non-archived) thread when sending a message, the backend MUST auto-create one with the default title before persisting the message.
- **FR-024**: When `OPENROUTER_API_KEY` (or equivalent LLM client config) is missing/invalid, the backend MUST fall back to a deterministic stub assistant response `"[F13 stub: LLM non configuré]"` and still emit a complete SSE envelope (`text_delta` + `message_done`). Tests run in this mode by default.
- **FR-025**: The `context_json` whitelist MUST be enforced server-side: extra/unknown fields cause HTTP 422; allowed keys are exactly `{page, entity_type, entity_id, selection}`.
- **FR-026**: Embedding computation MUST use FastAPI `BackgroundTasks` (non-blocking) after the assistant turn is persisted. Errors leave `embedding=NULL`; the row remains valid.
- **FR-027**: The `/me/events` SSE channel MUST be backed by an in-process asyncio fan-out keyed by `account_id`; subscribers MUST disconnect cleanly on client close. Cross-account leakage MUST be impossible by construction (no per-connection client-side filter).

### Key Entities *(include if feature involves data)*

- **ChatThread**: A logical conversation between one PME user and the assistant. Belongs to an account (tenant). Has a title, archived flag, and timestamps. One thread groups many messages.
- **ChatMessage**: A single utterance in a thread. Carries a role, textual content, optional structured payload, optional page context at send time, and an optional vector embedding for retrieval.
- **PageContext**: The whitelist-bound snapshot describing where the user was when sending a message: page path, entity type, entity id, optional selection.
- **EntityUpdateEvent**: A multi-tenant-scoped server event broadcast to all sessions of an account, signaling that an entity has changed and any UI displaying it should reload.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can complete a "hello" round-trip (send + receive an assistant reply) in under 3 seconds end-to-end on a typical connection.
- **SC-002**: Navigating between three different pages preserves the active thread, the scroll position at the bottom, and the open/closed state in 100% of cases.
- **SC-003**: Streaming output of the assistant is visible to the user before the full message is computed (first visible token under 1.5 seconds for a typical short reply).
- **SC-004**: 100% of persisted user messages have a non-null `context_json` that conforms to the whitelist schema.
- **SC-005**: When an `entity_updated` event is emitted for an entity displayed on the current page, the UI reflects the new value within 2 seconds without page reload.
- **SC-006**: Cross-tenant leakage tests show zero events or messages from another account reaching a user's session, under all tested scenarios.
- **SC-007**: Accessibility audit (manual): focus trap, ESC, ARIA roles all pass on the chat shell.

## Assumptions

- Authentication and `account_id`/`user_id` propagation are already provided by F02 (auth-roles-rls) and the FastAPI dependency stack.
- The audit log infrastructure (F04) is already available and append-only.
- The `chat_message` table already exists from F01; F13 enriches it (adds `payload_json`, `context_json`, `embedding`, `role` if missing) via a non-destructive migration.
- A Voyage AI embeddings client is already available in the backend (F03).
- The OpenRouter LLM client (minimax-m2.7) is configured; F13 only needs to invoke it in streaming mode and forward the JSON envelope.
- Server-Sent Events are sufficient for both the assistant streaming and the `entity_updated` channel; WebSocket is NOT required for MVP.
- Mobile UX uses dynamic viewport units (`dvh`) to handle the virtual keyboard.
- Embedding failures are non-blocking: the message is saved, the embedding is filled later or stays null.
- LLM-side title generation, mutation tools, structured response widgets, RAG memory, and skills are all OUT OF SCOPE for F13.
