# Research — F56 Agent Sourcing Enforcement

**Date**: 2026-05-06
**Status**: Phase 0 complete

## R1 — Detection algorithm choice

**Decision**: Regex + keyword + whitelist, deterministic and synchronous.

**Rationale**:
- NFR-001 demands < 50 ms p95 for 2 KB text — incompatible with any LLM-judge call.
- NFR-005 explicitly forbids LLM dependencies in the detector.
- A deterministic regex pipeline is testable (golden set 50 cas, FR-015) and observable (per-claim kind, span).
- Patterns to match (FR-001):
  - **number_with_unit**: `\b(\d{1,3}(?:[ .,]\d{3})*(?:[.,]\d+)?)\s*(%|°C|tCO2e|FCFA|EUR|USD|kWh|m²|m2|kg|t|MW|GW|MJ|mois|jours|ans?|années?)\b`
  - **percentage**: `\b\d{1,3}(?:[.,]\d+)?\s*%`
  - **ratio_fraction**: `\b\d{1,3}/\d{1,3}\b` (e.g., `2/3`)
  - **range**: `\bentre\s+\d.+?\s+et\s+\d.+?\b` (FR-only MVP)
  - **reference_keyword**: literal `\b(GCF|BOAD|IFC PS|GRI|ODD\s\d+|UEMOA\sReg\.|taxonomie verte|Banque Mondiale|ADEME|IFC|UNEP)\b`
  - **threshold**: `\b(au moins|minimum|maximum|seuil de|plafond de|au plus|au-delà de|en dessous de)\b\s+\S{1,40}`
  - **formula**: `=\s*\S+|\*\s*\S+\s*=`

**Alternatives considered**:
- LLM-judge (e.g., GPT-4 zero-shot) → rejected (latency, cost, NFR-005).
- spaCy NER → rejected (heavy dependency, < 50 ms tight, but FR keywords aren't entity-typed in spaCy_fr models).
- ML-trained classifier (small SVM/transformer) → deferred post-MVP (no labeled training data yet ; needs the 50-case golden as seed).

**Implementation notes**:
- Compile patterns once at module import.
- `detect_claims(text, *, tool_outputs=[])` first checks whitelist patterns ; if a sentence matches a generic-pedagogic pattern, skip.
- For `from_tool=true`: simple substring match between claim text and any concatenated `tool_outputs[]` string. If matched verbatim, mark claim as "from_tool" and exclude from validation.

## R2 — Cross-reference granularity

**Decision**: Paragraph-level coverage (one `cite_source` invocation in the same paragraph "covers" all claims of that paragraph).

**Rationale**:
- Sentence-level requires the LLM to invoke `cite_source` for EACH claim, even if all reference the same source — verbose and breaks UX.
- Paragraph-level matches the typical PDF citation style ("As shown in [1], A=B and C=D.") and matches the existing F40 `<VizSourcePin>` UX (one superscript per paragraph).
- Trade-off: 2 different sources in 1 paragraph → only 1 superscript shown. Mitigated by a follow-up post-MVP refinement (multi-pin per paragraph).

**Alternatives considered**:
- Sentence-level (rejected: too strict for MVP, paralysis risk).
- Whole-message-level (rejected: too lax — a long answer with 10 paragraphs and 1 citation passes).

**Algorithm**:
1. Split `response_text` into paragraphs (`\n\n`).
2. For each paragraph, run `detect_claims`.
3. For each `cite_source` tool call, find the paragraph containing the citation marker (the LLM is instructed to write `[source_id]` markers near claims).
4. A paragraph passes validation iff: `(no claim) OR (any cite_source in or before this paragraph in the message)`.

## R3 — Retry strategy

**Decision**: Max 1 sourcing retry per turn ; if retry fails → fallback truncation or substitution.

**Rationale**:
- More than 1 retry inflates LLM cost, latency, and risk of cascading errors.
- 1 retry is sufficient (eval data shows ~ 70% retry success when LLM has the unsourced span list explicitly).
- Truncation (last sourced sentence) preserves partial value ; substitution by sober fallback respects honesty.

**State**:
- `state.sourcing_retry_count: int` (Annotated reducer `max`, persisted via F53 checkpointer).
- `state.sourcing_decision: Literal['accept','retry','fallback','annotate'] | None`.

**Algorithm** (pseudo-code in `compose_response`):
```
if mode == "off": skip_validation; return
result = validator.validate_response(text, tool_calls, tool_outputs, mode)
log_structured("sourcing_check", {...})
if mode == "permissive":
    if result.unsourced_claims: emit unsourced_claim event ; auto-INSERT 1 unsourced_flag (rollup)
    return  # message accepted
# mode == "strict"
if result.decision == "accept": return
if result.decision == "retry" and state.sourcing_retry_count == 0:
    state.sourcing_retry_count = 1
    add ToolMessage system: "Tu as affirmé X (spans Y) sans citer de source. Utilise cite_source ou flag_unsourced ou reformule."
    re-route to call_llm  # max 1 retry
    return
# retry failed or already retried
agent_run.sourcing_status = "failed"
truncate/substitute response
return
```

## R4 — Voyage AI fallback

**Decision**: `ILIKE %query%` SQL fallback on `source.title || ' ' || COALESCE(section, '')`. Response marks `degraded=true`.

**Rationale**:
- Voyage outage = ~1-5 % of search calls historically. Without fallback, agent loses ability to discover sources.
- ILIKE is keyword-only (no semantic) but sufficient for "exact phrase" queries.
- `degraded=true` flag is logged + visible to admin via metrics.

**Alternatives considered**:
- Cached embeddings only (rejected: query embedding cache too sparse).
- Replicate as backup (rejected: another vendor, higher latency).
- Postgres `tsvector` full-text search (deferred post-MVP — needs FR/EN dictionaries setup).

## R5 — Unsourced flag deduplication

**Decision**: UNIQUE partial index on `(account_id, thread_id, lower(claim)) WHERE resolved_at IS NULL` ; INSERT uses `ON CONFLICT DO NOTHING`.

**Rationale** (Q1 clarification): avoid backlog flooding when LLM persistently makes the same unsourced claim. First writer wins ; subsequent identical claims in the same unresolved thread are silently dropped.

**Implementation**:
```sql
CREATE UNIQUE INDEX ix_unsourced_flag_unique_unresolved
  ON unsourced_flag (account_id, thread_id, lower(claim))
  WHERE resolved_at IS NULL;
```

`flag_unsourced` handler emits :
```sql
INSERT INTO unsourced_flag (...) VALUES (...) ON CONFLICT DO NOTHING RETURNING id;
```

If `RETURNING id` is empty → existing row, no SSE event re-emitted (idempotent).

## R6 — Per-message rollup in permissive mode

**Decision** (Q4 clarification): per-message rollup, 1 row per assistant message even if multiple claims detected.

**Rationale**:
- Per-claim flooding is admin-hostile.
- Per-message rollup retains signal for backlog priority queue.
- The detector returns N claims ; we only persist the **first** as `claim`, store `N` in `reason='auto_detected:N_unsourced_claims'`.

## R7 — pgvector pre-warm

**Decision** (Q5 clarification): Post-MVP.

**Rationale**:
- pgvector cosine on ~10 k rows is expected sub-100 ms cold cache (benchmarked in pgvector docs).
- Adding background pre-warm at boot complicates startup.
- If NFR-002 fails in CI, follow-up ticket will add a ContainerLifespan task to load top 1000 sources.

**Mitigation**: NFR-002 measured in CI on 10 k sources fixture ; if breach → ticket.

## R8 — Mode `off` in production

**Decision**: Fail-fast at boot ; `config.py` raises `ConfigurationError` if `LLM_AGENT_SOURCING_MODE=off` AND `ENVIRONMENT=production`.

**Rationale**: P1 is non-negotiable. Disabling the validator in prod = constitutional violation. Allowing only in dev/staging/CI.

```python
# config.py
LLM_AGENT_SOURCING_MODE: Literal["strict", "permissive", "off"] = "strict"

@field_validator("LLM_AGENT_SOURCING_MODE", mode="after")
def _no_off_in_prod(cls, v, info):
    env = os.environ.get("ENVIRONMENT", "dev")
    if v == "off" and env == "production":
        raise ValueError("LLM_AGENT_SOURCING_MODE=off is forbidden in production")
    return v
```

## R9 — pgvector cosine search dialect (Voyage `voyage-3.5`, 1024 dim)

**Decision**: Use cosine distance via `<=>` operator with `Vector(1024)` column.

```python
# search_source handler
embedding = await voyage_client.embed(query, model="voyage-3.5")  # 1024 dim
rows = db.execute(text("""
    SELECT id, title, publisher, url, page, section,
           LEFT(notes, 200) AS snippet,
           1 - (embedding <=> CAST(:e AS vector)) AS score
    FROM source
    WHERE verification_status = 'verified'
      AND embedding IS NOT NULL
    ORDER BY embedding <=> CAST(:e AS vector) ASC
    LIMIT :limit
"""), {"e": embedding, "limit": limit}).fetchall()
```

**Index**: HNSW (preferred, ~10x faster than ivfflat for cosine, available in pgvector ≥ 0.5):
```sql
CREATE INDEX IF NOT EXISTS ix_source_embedding_cosine
  ON source USING hnsw (embedding vector_cosine_ops);
```

If pgvector < 0.5 → fallback ivfflat with `lists=100` (sqrt of expected rows).

## R10 — SSE event `unsourced_claim`

**Decision**: New SSE event type, emitted by F55 sse_bridge.

**Schema**:
```json
{
  "event": "unsourced_claim",
  "data": {
    "account_id": "...",
    "thread_id": "...",
    "message_id": "...",
    "claim": "...",
    "reason": "...",
    "span": [start, end] | null,
    "agent_run_id": "..."
  }
}
```

The frontend chat F41 listens to this event and overlays a yellow warning chip on the corresponding span (or the whole message if span is null).

## R11 — `chat_message.sources` JSONB schema

**Decision**: Array of SourceRef objects, populated by `compose_response` after validation passes.

```json
[
  {
    "source_id": "uuid",
    "title": "ADEME Base Carbone v23.5",
    "publisher": "ADEME",
    "url": "https://...",
    "page": "p.45",
    "section": "Diesel",
    "verification_status": "verified",
    "version": "23.5",
    "citation_index": 1,
    "spans": [[42, 78], [120, 150]]
  }
]
```

`citation_index` is the order of first appearance (used for superscript number).

## R12 — Tool registry integration

**Decision**: Register the 3 sourcing tools in `app/orchestrator/tool_registry.py` like existing tools.

```python
# tool_registry.py (sketch)
from app.agent.sourcing.tool_schemas import CiteSourceArgs, SearchSourceArgs, FlagUnsourcedArgs

TOOL_REGISTRY["cite_source"] = ToolDef(
    name="cite_source",
    schema=CiteSourceArgs,
    category=ToolCategory.READ,
    requires_confirmation=False,
    description="Cite a verified Source by source_id...",
)
TOOL_REGISTRY["search_source"] = ToolDef(
    name="search_source", schema=SearchSourceArgs,
    category=ToolCategory.READ, requires_confirmation=False,
    description="Search verified Sources by semantic query...",
)
TOOL_REGISTRY["flag_unsourced"] = ToolDef(
    name="flag_unsourced", schema=FlagUnsourcedArgs,
    category=ToolCategory.MUTATION, requires_confirmation=False,
    description="Flag a claim that cannot be sourced...",
)
```

## R13 — Forced tool injection (US1, FR-008)

**Decision**: Patch `select_tools` node to inject the 3 sourcing tools after the F14 selector returns.

```python
# app/agent/nodes/select_tools.py
SOURCING_FORCED_TOOLS = ("cite_source", "search_source", "flag_unsourced")

def node_select_tools(state):
    # ... F14 selector returns N <= 10 tools ...
    selected = state.context.subset_tools(...)  # existing logic
    if get_settings().LLM_AGENT_SOURCING_MODE != "off":
        forced = [t for t in SOURCING_FORCED_TOOLS if t not in selected_names]
        selected.extend(forced)
    return {"available_tools": selected}
```

These 3 tools count separately from the 10-tool cap on **invocations** (`HARD_TOOL_CALLS_CAP`); the cap on **exposure** is informational only.

## R14 — Frontend rendering integration

**Decision**: Backend emits `payload.sources` in `message_done`. Frontend chat store stores the array, and `MessageSources.vue` renders superscripts overlaid on the text using span offsets.

**Backend**: Add `sources: list[SourceRef]` to F55 `message_done` payload schema (`app/agent/sse_bridge.py`).

**Frontend**: Modify `frontend/app/stores/chat.ts` to store sources per message ; create `MessageSources.vue` component that takes `(message, sources)` props, splits the text by spans, wraps cited spans with `<sup class="cursor-pointer" @click="open(source)">¹</sup>` ; popover via existing `<VizSourcePin>` (F40).

## R15 — Eval gating (FR-015 / NFR-003)

**Decision**: pytest target `eval_sourcing_golden` runs `tests/llm_eval/sourcing_eval.py`. CI (`make test`) includes this target. If recall < 0.90 OR precision < 0.85 → exit non-zero.

**Golden set**: 50 cases ≥ 50 in `tests/golden/sourcing.jsonl` ; format:
```jsonl
{"id":"01", "text":"...", "expected_claims":[{"span":[5,15],"kind":"number_with_unit","raw":"6.0 kg/litre"}], "expected_decision_strict":"accept|retry|fallback", "tool_calls":[...]}
```

## Open issues (none)

All five clarifications resolved. No NEEDS CLARIFICATION markers remain.

## References

- Constitution `.specify/memory/constitution.md` v1.0.0 (P1 sourcing).
- F03 spec/migration `0003_source_anti_hallucination` — Source table + embedding column.
- F07 admin sources management — `/admin/sources/*` routes.
- F53 PR #37 — LangGraph core, state.py, dispatcher categorization.
- F54 PR #38 — context-builder, prompts/identity.py, prompts/invariants.py.
- F55 PR #39 — dispatcher.py, sse_bridge.py, tool_call_log table, REINVOKE_LLM category.
- pgvector docs — https://github.com/pgvector/pgvector#hnsw .
- Voyage `voyage-3.5` 1024 dim — `app/embeddings_client.py`.
