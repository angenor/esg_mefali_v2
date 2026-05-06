---

description: "Task list — F56 Agent Sourcing Enforcement"
---

# Tasks: Agent Sourcing Enforcement (F56)

**Input**: Design documents from `specs/056-agent-sourcing-enforcement/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY (constitution: 80%+ coverage, TDD-first). Test tasks precede implementation tasks within each user story.

**Organization**: Tasks are grouped by user story (US1-US10) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1..US10)
- File paths are absolute or repo-relative (`backend/...`, `frontend/...`).

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`, `backend/alembic/versions/`
- Frontend: `frontend/app/`, `frontend/tests/`
- Extension sidepanel: `extension/sidepanel/src/`, `extension/sidepanel/__tests__/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for F56.

- [ ] T001 Create empty package directory `backend/app/agent/sourcing/` with `__init__.py` and `models.py` skeleton (Claim dataclass, ClaimKind Literal, SourcingMode Literal, SourcingDecision Literal, SourcingValidationResult Pydantic, SourceRef Pydantic — see `specs/056-agent-sourcing-enforcement/data-model.md` §5)
- [ ] T002 [P] Add `LLM_AGENT_SOURCING_MODE: Literal["strict","permissive","off"] = "strict"` to `backend/app/config.py` (Settings class) with `field_validator` that raises ValueError when `mode='off'` AND `ENVIRONMENT=production` (FR-007, R8)
- [ ] T003 [P] Add tool-schemas Pydantic models `CiteSourceArgs`, `SearchSourceArgs`, `FlagUnsourcedArgs` (with `extra='forbid'` and bounded fields) in `backend/app/agent/sourcing/tool_schemas.py` per `contracts/tool-registry.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DB schema, RLS, model registration, state augmentation. MUST complete before any user-story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Write alembic migration `backend/alembic/versions/0035_f56_unsourced_flag_and_sourcing_columns.py`: creates `unsourced_flag` table (id, account_id, user_id, agent_run_id, thread_id, message_id, claim, reason, source_of_change, created_at, resolved_at, resolved_by, version), the 3 indexes (account_created, partial UNIQUE for dedup, unresolved), RLS policy `unsourced_flag_account_isolation`, REVOKE/GRANT, ALTER agent_run.sourcing_status, ALTER chat_message.sources JSONB + GIN index, and conditional pgvector index on source.embedding (HNSW with ivfflat fallback). See `data-model.md` §1-4.
- [ ] T005 Create SQLAlchemy ORM model `UnsourcedFlag` in `backend/app/models/unsourced_flag.py` with all columns + relationships (`Account`, `AccountUser` for `user_id`/`resolved_by`, `AgentRun`, optional `ChatThread`/`ChatMessage`).
- [ ] T006 Wire `UnsourcedFlag` import in `backend/app/models/__init__.py` so alembic autogenerate sees it (also re-exports for tests).
- [ ] T007 Augment `backend/app/agent/state.py` `AgentState`: add fields `sourcing_retry_count: Annotated[int, _max_reducer] = 0`, `sourcing_decision: SourcingDecision | None = None`, `sourcing_validation_result: SourcingValidationResult | None = None`. Add `_max_reducer` if not already present (idempotent reducer that returns the maximum of current state and patch).
- [ ] T008 [P] Run `make migrate` locally and verify schema (psql `\d unsourced_flag`, `\di+ source*`, `SELECT column_name FROM information_schema.columns WHERE table_name IN ('agent_run','chat_message')`).
- [ ] T009 [P] Add E2E test fixture `backend/tests/conftest.py` (or feature-scoped) seeding 5 verified Sources with embeddings (placeholder vector ok) for use across F56 tests.

**Checkpoint**: Foundation ready — user story work can begin.

---

## Phase 3: User Story 1 — Tools sourcing toujours disponibles (Priority: P1) 🎯 MVP

**Goal**: Force `cite_source`, `search_source`, `flag_unsourced` into `state.available_tools` at every turn (when `mode != off`), regardless of the F14 selector. Register these 3 tools in TOOL_REGISTRY.

**Independent Test**: Launch an agent run with a selector returning 0 business tools — verify `available_tools` contains the 3 sourcing tools and the 10-tool métier cap is unaffected.

### Tests for User Story 1

- [ ] T010 [P] [US1] Write unit test `backend/tests/unit/test_tool_registry_sourcing_tools.py` asserting `TOOL_REGISTRY["cite_source"].category == ToolCategory.READ`, `TOOL_REGISTRY["search_source"].category == ToolCategory.READ`, `TOOL_REGISTRY["flag_unsourced"].category == ToolCategory.MUTATION`, and Pydantic schemas reject extra fields.
- [ ] T011 [P] [US1] Write integration test `backend/tests/integration/test_select_tools_force_sourcing.py` covering: (a) 7-tool métier selector → available_tools = 10 (7+3); (b) 10-tool selector → 13 exposed but cap on invocations stays 10; (c) `mode='off'` → no forcing.

### Implementation for User Story 1

- [ ] T012 [US1] Register the 3 tools in `backend/app/orchestrator/tool_registry.py`: `cite_source` (READ, schema=CiteSourceArgs), `search_source` (READ, schema=SearchSourceArgs), `flag_unsourced` (MUTATION, schema=FlagUnsourcedArgs) with full descriptions and use-when/don't-use-when docstrings (FR-003, FR-004, FR-005).
- [ ] T013 [US1] Patch `backend/app/agent/nodes/select_tools.py`: add constant `SOURCING_FORCED_TOOLS = ("cite_source","search_source","flag_unsourced")`; in the node body, after the F14 selector returns, if `settings.LLM_AGENT_SOURCING_MODE != "off"`, append the missing forced tools to `available_tools` (FR-008).

**Checkpoint**: US1 complete — tests T010, T011 pass.

---

## Phase 4: User Story 2 — `cite_source` validé contre la base (Priority: P1)

**Goal**: Implement the `cite_source` handler that verifies a source exists and is `verified` in DB, returns serialized metadata or structured error.

**Independent Test**: Invoke `cite_source(<unknown UUID>)` → `source_not_found` error; `cite_source(<pending source>)` → `source_unverified`; `cite_source(<verified source>)` → metadata returned.

### Tests for User Story 2

- [ ] T014 [P] [US2] Write integration test `backend/tests/integration/test_cite_source_handler.py` with 4 scenarios: (a) unknown UUID, (b) pending source, (c) outdated source (Q3 — also rejected), (d) verified source. Assert `tool_call_log.status` and structured error fields.

### Implementation for User Story 2

- [ ] T015 [US2] Implement handler `backend/app/agent/handlers/cite_source.py` per `contracts/tool-registry.md` §Tool 1 — query `Source` by id, check `verification_status == 'verified'` strictly, return `{source_id, title, publisher, url=canonical_url||url, page, section, version, verification_status}` or `{error, current_status, hint}`.
- [ ] T016 [US2] Register `cite_source_handler` in `backend/app/agent/dispatcher.py` `_REINVOKE_HANDLERS` mapping (replace stub mentioned in `app/agent/dispatcher.py:322`).

**Checkpoint**: US2 complete — test T014 passes.

---

## Phase 5: User Story 3 — `search_source` semantic + ILIKE fallback (Priority: P1)

**Goal**: Implement `search_source` handler returning top-5 verified sources via Voyage embedding + pgvector cosine, with `ILIKE` fallback on Voyage outage.

**Independent Test**: With 50 verified sources fixture, `search_source(query="ADEME diesel")` returns ADEME source as top-1 in <500ms; mock Voyage to throw → ILIKE fallback returns and `degraded=true`.

### Tests for User Story 3

- [ ] T017 [P] [US3] Write integration test `backend/tests/integration/test_search_source_handler.py` with 3 scenarios: (a) Voyage OK → cosine top-5 sorted by score, (b) Voyage error → ILIKE fallback `degraded=true`, (c) empty result with `no_match` hint.
- [ ] T018 [P] [US3] Write perf test `backend/tests/perf/test_sourcing_perf.py::test_search_source_p95` with 10 k seeded sources fixture; assert p95 < 500 ms (NFR-002).

### Implementation for User Story 3

- [ ] T019 [US3] Implement handler `backend/app/agent/handlers/search_source.py` per `contracts/tool-registry.md` §Tool 2: embedding via `app.embeddings_client.embed(query, model="voyage-3.5")`, pgvector `ORDER BY embedding <=> CAST(:e AS vector) ASC LIMIT :limit` with `WHERE verification_status='verified'`, returning `{results, degraded:false}`. On `VoyageError`/timeout, fallback `ILIKE` query, `degraded:true`.
- [ ] T020 [US3] Register `search_source_handler` in `backend/app/agent/dispatcher.py` `_REINVOKE_HANDLERS`.

**Checkpoint**: US3 complete — tests T017, T018 pass.

---

## Phase 6: User Story 4 — `flag_unsourced` + dedup + SSE (Priority: P1)

**Goal**: Implement `flag_unsourced` mutation handler with `ON CONFLICT DO NOTHING` dedup and SSE event emission.

**Independent Test**: Invoke `flag_unsourced(claim, reason)` → row inserted under RLS, SSE `unsourced_claim` event emitted; second identical invocation in same thread → silent dedup.

### Tests for User Story 4

- [ ] T021 [P] [US4] Write integration test `backend/tests/integration/test_flag_unsourced_handler.py`: (a) successful insert, audit_log entry, SSE emitted; (b) duplicate within same thread → ON CONFLICT DO NOTHING; (c) RLS enforcement (different account_id → no visibility); (d) length validation Pydantic.
- [ ] T022 [P] [US4] Write integration test `backend/tests/integration/test_unsourced_flag_admin_resolve.py`: admin role updates `resolved_at`/`resolved_by` ; app_user role UPDATE rejected (P3 audit append-only).

### Implementation for User Story 4

- [ ] T023 [US4] Implement handler `backend/app/agent/handlers/flag_unsourced.py` per `contracts/tool-registry.md` §Tool 3 — INSERT with `ON CONFLICT (account_id, thread_id, lower(claim)) WHERE resolved_at IS NULL DO NOTHING RETURNING id`, audit_log via `ctx.audit_logger`, SSE `unsourced_claim` via `ctx.event_bus_publisher`.
- [ ] T024 [US4] Register `flag_unsourced_handler` in `backend/app/agent/mutation_handlers.py` registry (since it's MUTATION, follows F55 mutation flow).
- [ ] T025 [US4] Add `unsourced_claim` to `KNOWN_EVENTS` in `backend/app/agent/sse_bridge.py` so the bridge accepts and forwards the event type (FR-005).

**Checkpoint**: US4 complete — tests T021, T022 pass.

---

## Phase 7: User Story 5 — Détecteur de claims factuels (Priority: P1)

**Goal**: Synchronous regex+keyword detector with whitelist support, < 50 ms p95 for 2000-char text.

**Independent Test**: 50-case golden set passes recall ≥ 0.90 and precision ≥ 0.85.

### Tests for User Story 5

- [ ] T026 [P] [US5] Create golden set `backend/tests/golden/sourcing.jsonl` with 50 cases (each: text, expected_claims with span+kind+raw, optional from_tool flag). Distribution: ≥ 5 per ClaimKind, ≥ 10 whitelist hits, ≥ 5 from_tool examples.
- [ ] T027 [P] [US5] Write unit tests `backend/tests/unit/test_sourcing_detector.py`: ≥ 3 positive cases per ClaimKind, whitelist hit returns empty list, from_tool flag set when text matches tool_outputs[].
- [ ] T028 [P] [US5] Write perf test `backend/tests/perf/test_sourcing_perf.py::test_detector_p95` — 2000-char input, p95 < 50 ms (NFR-001).
- [ ] T029 [US5] Write golden eval test `backend/tests/llm_eval/sourcing_eval.py` (also runnable as `pytest -m eval`) — loads `tests/golden/sourcing.jsonl`, computes precision/recall, asserts thresholds (FR-015 / NFR-003). **Depends on T026 (golden set must exist) and T032 (detector implementation must exist) — NOT parallel.**

### Implementation for User Story 5

- [ ] T030 [US5] Implement `backend/app/agent/sourcing/whitelist.py` with `WHITELIST_PATTERNS` (≥ 20 compiled regex) and `is_whitelisted(sentence) -> bool` (FR-014).
- [ ] T031 [US5] Implement `backend/app/agent/sourcing/normalizer.py` with `normalize_claim(text) -> str` (lowercase, collapse whitespace, strip punctuation) for dedup keys.
- [ ] T032 [US5] Implement `backend/app/agent/sourcing/detector.py::detect_claims(text, tool_outputs=[])` with all 7 ClaimKind regex patterns, whitelist filter on sentence boundary, from_tool check via substring match, sorted+dedup by span (FR-001).

**Checkpoint**: US5 complete — tests T026-T029 pass; golden set eval ≥ 0.90 / 0.85.

---

## Phase 8: User Story 6 — Validateur de sourçage avec retry (Priority: P1)

**Goal**: Cross-reference detector ↔ cite_source invocations and apply mode policy (strict / permissive / off). Drive retry & fallback in `compose_response`.

**Independent Test**: 4 strict-mode scenarios (accept / retry-then-accept / retry-then-fallback / fallback-substitute) pass; permissive mode annotates without blocking; off mode bypasses.

### Tests for User Story 6

- [ ] T033 [P] [US6] Write unit tests `backend/tests/unit/test_sourcing_validator.py`: 4 decisions (accept/retry/fallback/annotate), paragraph coverage logic, mode='off' short-circuit, sourcing_retry_count=1 → fallback.
- [ ] T034 [P] [US6] Write integration test `backend/tests/integration/test_compose_response_retry.py`: full agent run with mocked LLM. (a) strict: unsourced → retry → accept ; (b) strict: 2 retries failed → fallback substitute ; (c) permissive: annotate + auto unsourced_flag (per-message rollup, 1 row even if N claims) ; (d) off: skip validation.

### Implementation for User Story 6

- [ ] T035 [US6] Implement `backend/app/agent/sourcing/validator.py::validate_response(response_text, tool_calls, *, tool_outputs=[], mode, sourcing_retry_count=0) -> SourcingValidationResult` per `contracts/sourcing-validator.md` (paragraph-level coverage R2, structured logging R-FR-016).
- [ ] T036 [US6] Modify `backend/app/agent/nodes/compose_response.py` to call `validate_response` post-LLM, handle 4 decisions:
  - `accept` → emit message + `chat_message.sources` patch + `agent_run.sourcing_status` patch.
  - `retry` (max 1) → append ToolMessage system listing unsourced spans, increment `sourcing_retry_count`, route back to `call_llm`.
  - `fallback` → truncate to last sourced paragraph or substitute fallback string, mark `agent_run.sourcing_status='failed'`, set `degraded=true` in payload (FR-008/FR-009/FR-010).
  - `annotate` (permissive) → emit message + auto-create 1 `unsourced_flag` per message (Q4 rollup, ON CONFLICT DO NOTHING), emit `unsourced_claim` SSE.
- [ ] T037 [US6] Implement `backend/app/agent/sourcing/validator.py` helper `aggregate_sources_from_calls(tool_calls, validation_result) -> list[SourceRef]` to populate `chat_message.sources` JSONB and `message_done.payload.sources` (FR-011).

**Checkpoint**: US6 complete — tests T033, T034 pass.

---

## Phase 9: User Story 7 — Annotation visuelle des chips Source (Priority: P1)

**Goal**: Frontend chat F41 + extension sidepanel F52 render superscripts cliquables ouvrant le popover `<VizSourcePin>` (F40) avec les détails source.

**Independent Test** (Playwright E2E): a message with `payload.sources=[{...}]` is rendered in the chat with numbered superscripts ; clicking opens popover with title, publisher, URL.

### Tests for User Story 7

- [ ] T038 [P] [US7] Write Playwright E2E test `frontend/tests/e2e/chat-sources-rendering.spec.ts`: navigate to /chat with a fixture conversation, assert superscripts are visible, click → popover with title, publisher, URL, "Ouvrir le PDF" button. **MUST also cover an `unsourced_claim` SSE event scenario** asserting that a yellow warning chip appears on the corresponding span (FR-005 frontend coverage).
- [ ] T039 [P] [US7] Write vitest unit test `extension/sidepanel/__tests__/chat-sources.spec.ts`: simulate SSE message_done with sources → chat store contains the array; component renders superscripts.

### Implementation for User Story 7

- [ ] T040 [US7] Modify `frontend/app/stores/chat.ts` (Pinia) to store `payload.sources` per message ID upon receiving `message_done` SSE event.
- [ ] T041 [US7] Create `frontend/app/components/chat/MessageSources.vue` — receives `(message_text, sources: SourceRef[])` props, splits text by spans, wraps cited spans in `<sup class="cursor-pointer" @click="open(s)">¹</sup>`, renders `<VizSourcePin>` (F40) on click. Outdated sources show orange badge.
- [ ] T042 [US7] Wire `<MessageSources>` into the existing chat message component in `frontend/app/pages/chat/[id].vue` (or wherever F41 renders messages).
- [ ] T043 [US7] Mirror minimal rendering in `extension/sidepanel/src/views/chat/ChatView.vue` — read `sources` from store, render simplified inline numbered chips (no popover; click opens URL in new tab).

**Checkpoint**: US7 complete — tests T038, T039 pass.

---

## Phase 10: User Story 8 — Annexe "Sources et références" (Priority: P1, déléguée F49)

**Goal**: Backend exposes the data needed for the F49 PDF annex (sources cited per message). F56 only **provides the data**; F49 owns the PDF rendering.

**Independent Test**: Query `SELECT m.sources FROM chat_message m WHERE m.thread_id = ?` returns the JSONB array used by F49; F49's annex generation function consumes it without F56-side changes.

### Implementation for User Story 8

- [ ] T044 [US8] Add helper `backend/app/services/source_aggregation.py::aggregate_thread_sources(thread_id: UUID) -> list[SourceRef]` that aggregates unique sources across all `chat_message.sources` for a thread (deduplicated by source_id, preserves first-citation order).
- [ ] T045 [US8] Add unit test `backend/tests/unit/test_source_aggregation.py` for `aggregate_thread_sources` (empty, 1 message, multiple messages with overlapping sources).
- [ ] T046 [US8] Document in `quickstart.md` how F49 will call `aggregate_thread_sources` to build the PDF annex (no F49 code changes in F56 scope).

**Checkpoint**: US8 complete — F49 has the API to build the annex.

---

## Phase 11: User Story 9 — Métriques de compliance sourçage (Priority: P2)

**Goal**: Admin endpoint `GET /admin/agent/metrics/sourcing?period=7d|30d|all` returns compliance KPIs.

**Independent Test**: After ≥ 100 simulated agent_runs, endpoint returns valid Pydantic response with all expected fields and `403` for non-admin.

### Tests for User Story 9

- [ ] T047 [P] [US9] Write integration test `backend/tests/integration/test_admin_metrics_sourcing.py`: (a) admin auth → 200 with valid Pydantic shape, (b) non-admin → 403, (c) period validation, (d) computed values match SQL ground truth, (e) cache hit/miss path.

### Implementation for User Story 9

- [ ] T048 [US9] Implement `backend/app/admin/agent_metrics.py::router` with `GET /admin/agent/metrics/sourcing` endpoint, dependency `admin_required`, Pydantic response `SourcingMetricsResponse` per `contracts/admin-metrics.md`. SQL queries from research §R + admin sentinel context.
- [ ] T049 [US9] Mount router in `backend/app/main.py`: `app.include_router(agent_metrics.router, prefix="/admin/agent/metrics", tags=["admin", "agent"])`.
- [ ] T050 [US9] Add 5-minute Redis caching in the endpoint (key `admin:metrics:sourcing:{period}`) using existing `app/utils/cache.py` infrastructure (or add minimal in-memory fallback if Redis is mocked in tests).

**Checkpoint**: US9 complete — test T047 passes.

---

## Phase 12: User Story 10 — Liste blanche de claims génériques (Priority: P2 — already implemented in US5)

**Goal**: 20+ whitelist patterns documented and tested.

**Independent Test**: Whitelist 20+ patterns + 0 false-rejects on golden set.

### Tests for User Story 10

- [ ] T051 [P] [US10] Write unit test `backend/tests/unit/test_sourcing_whitelist.py`: each WHITELIST_PATTERNS pattern has ≥ 1 positive case ; specific real claims like "Le seuil de 50 M USD" NOT whitelisted by any pattern.

### Implementation for User Story 10

- [ ] T052 [US10] Audit `WHITELIST_PATTERNS` (already created in T030) and ensure ≥ 20 patterns covering: generic adverbs ("En général", "Typiquement", "Cela dépend"), conditional ("Selon le cas", "Si vous avez"), pedagogical ("Imaginons que"), opinion markers ("À mon avis"), abstract ("Les PME en général").

**Checkpoint**: US10 complete — test T051 passes.

---

## Phase 13: Polish & Cross-Cutting Concerns

- [ ] T053 [P] Add structured logging `sourcing_check` (FR-016) to `backend/app/agent/nodes/compose_response.py` — emit one log line per validation pass with all required fields.
- [ ] T054 [P] Update `backend/app/agent/prompts/identity.py` (or `invariants.py`) to include a sourcing-instruction block that references `cite_source` / `search_source` / `flag_unsourced` and gives 2 examples (one sourced response, one with flag_unsourced) — F54 contract.
- [ ] T055 [P] Add E2E pytest `backend/tests/integration/test_sourcing_e2e_strict.py` (FR-020): real DB + mocked LLM ; 1 turn produces an unsourced claim → strict retry → second turn cites source → assert agent_run.sourcing_status='retried_ok' AND chat_message.sources contains the cited source.
- [ ] T056 [P] Add E2E pytest `backend/tests/integration/test_sourcing_e2e_permissive.py` (mode permissive): unsourced → annotate + 1 unsourced_flag row (rollup, not N rows) + SSE unsourced_claim event captured.
- [ ] T057 [P] Add validator perf test `backend/tests/perf/test_sourcing_perf.py::test_validator_p95` — assert p95 < 100 ms (NFR-008).
- [ ] T058 [P] Update `backend/pyproject.toml` if needed (verify `pgvector`, `voyageai` deps already declared by F03; otherwise add).
- [ ] T059 [P] Run `make lint` (ruff) and fix violations (ESG_MEFALI ruff config: line-length 100, select E,F,W,I,B,UP).
- [ ] T060 Run full `make test` and verify coverage ≥ 80% on the new `app/agent/sourcing/` package.
- [ ] T061 [P] Update `docs_et_brouillons/features/00-INDEX.md` marking F56 status `merged` once PR lands (post-implementation, not part of this branch but tracked).
- [ ] T062 Add `make sourcing-eval` target invoking `pytest tests/llm_eval/sourcing_eval.py -v` for CI gating.

---

## Dependencies

```text
Phase 1 (Setup)              → Phase 2 (Foundational)
Phase 2 (Foundational)       → Phase 3..12 (User Stories) [parallelizable amongst]
Phase 3..12                  → Phase 13 (Polish)

Within user stories:
US1 (T010-T013)              ← independent
US2 (T014-T016)              ← depends on US1 (handler registration uses tool_registry)
US3 (T017-T020)              ← depends on US1
US4 (T021-T025)              ← depends on US1; T024 depends on T012 register
US5 (T026-T032)              ← independent (pure logic, no DB)
US6 (T033-T037)              ← depends on US2, US4, US5 (validator uses cite_source results + detector + flag_unsourced auto)
US7 (T038-T043)              ← depends on US6 (consumes payload.sources)
US8 (T044-T046)              ← depends on US6 (chat_message.sources populated)
US9 (T047-T050)              ← depends on US6, US4 (queries unsourced_flag + chat_message.sources + agent_run.sourcing_status)
US10 (T051-T052)             ← depends on US5 (T030 whitelist module)
```

### Critical path (MVP)

`Setup → Foundational → US1 (T010-T013) → US2 (T014-T016) → US5 (T026-T032) → US6 (T033-T037)`

Once these 4 stories are done, the agent enforces P1 in strict mode end-to-end on the backend. US3, US4, US7-US9 add coverage and UX (top-tier MVP completeness but the P1 invariant is already enforced).

---

## Parallel Execution Examples

### Wave 1 (Setup, parallel)

```text
T002 [P] Add LLM_AGENT_SOURCING_MODE config
T003 [P] Add tool-schemas Pydantic models
```

### Wave 2 (Foundational, mostly serial, T008+T009 parallel)

```text
T004 → T005 → T006 → T007 → (T008 [P], T009 [P])
```

### Wave 3 (User Stories — high parallelism after foundation)

Once foundation is done, these can run in parallel:

```text
US1 tests:        T010 [P] [US1], T011 [P] [US1]
US3 tests:        T017 [P] [US3], T018 [P] [US3]
US4 tests:        T021 [P] [US4], T022 [P] [US4]
US5 tests:        T026 [P] [US5], T027 [P] [US5], T028 [P] [US5], T029 [P] [US5]
US7 tests:        T038 [P] [US7], T039 [P] [US7]
US9 tests:        T047 [P] [US9]
US10 tests:       T051 [P] [US10]
```

### Wave 4 (Polish, all parallel)

```text
T053 [P], T054 [P], T055 [P], T056 [P], T057 [P], T058 [P], T059 [P], T061 [P]
```

(T060 and T062 are sequential at the end.)

---

## E2E test files planned

Per the constitution (testing.md, FR-020 / FR-021), the following E2E tests are mandatory for F56:

### Backend pytest E2E

1. `backend/tests/integration/test_sourcing_e2e_strict.py` — strict mode happy path + retry + fallback (T055).
2. `backend/tests/integration/test_sourcing_e2e_permissive.py` — permissive mode + auto rollup + SSE event (T056).
3. `backend/tests/integration/test_compose_response_retry.py` — agent run with all 3 modes (T034).
4. `backend/tests/integration/test_admin_metrics_sourcing.py` — admin endpoint full flow (T047).

### Frontend Playwright E2E

1. `frontend/tests/e2e/chat-sources-rendering.spec.ts` — superscripts + popover render (T038).

### Extension vitest E2E

1. `extension/sidepanel/__tests__/chat-sources.spec.ts` — sidepanel rendering (T039).

### Performance / Eval

1. `backend/tests/perf/test_sourcing_perf.py` (T028, T018, T057) — NFR-001/002/008.
2. `backend/tests/llm_eval/sourcing_eval.py` (T029, gated by `make sourcing-eval`) — golden set 50 cases, NFR-003.

---

## Implementation Strategy (incremental delivery)

1. **MVP (Day 1–2)** : Setup + Foundational + US1 + US2 + US5 + US6 + structured logging (T053). At end of day 2, the agent enforces P1 strict mode on the backend with the detector and validator running.
2. **Day 3** : US3 (search_source), US4 (flag_unsourced + dedup), US7 (frontend rendering). End of day 3, full UX path is visible.
3. **Day 4** : US8 (aggregation helper), US9 (admin metrics), US10 (whitelist audit), Polish phase, perf + eval tests, full coverage report. End of day 4, F56 ships ready for PR.

Total estimate aligned with the 4 days in the original spec backlog (`docs_et_brouillons/features/56-agent-sourcing-enforcement.md`).

---

## Format Validation

All 62 tasks follow the strict checklist format:
- ✅ checkbox `- [ ]`
- ✅ Task ID (T001..T062 sequential)
- ✅ `[P]` marker on parallel tasks (different files, no incomplete deps)
- ✅ `[US1]..[US10]` story label on user-story phase tasks
- ✅ NO story label on Setup/Foundational/Polish phases
- ✅ Exact file paths in every implementation task
- ✅ Test tasks precede implementation tasks (TDD-first per constitution)
