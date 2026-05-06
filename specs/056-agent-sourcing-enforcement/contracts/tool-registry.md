# Contract — Tool Registry (F56 sourcing tools)

**Status**: Phase 1 (canonical)

## Overview

F56 registers 3 new tools in `app/orchestrator/tool_registry.py`. All three follow F53/F55 conventions :
- Pydantic v2 schemas with `model_config = ConfigDict(extra='forbid')`.
- Bounded string fields (`min_length`, `max_length`).
- Closed enums where applicable.
- Docstring with "use when / don't use when" sections.
- Categorization for F55 dispatcher (`READ` / `MUTATION`).

## Tool 1 — `cite_source`

### Purpose

Bind a verified `Source` (catalog F03/F07) to the current LLM response by `source_id`. The handler verifies the source exists and is `verification_status='verified'`. On success, the tool returns a `ToolMessage` containing the source metadata; the LLM uses this metadata to compose the final response with proper citation markers.

### Pydantic schema

```python
# app/agent/sourcing/tool_schemas.py
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class CiteSourceArgs(BaseModel):
    """Arguments for the cite_source tool.

    Use when:
    - You need to back a factual claim (number, threshold, formula, reference) with a verified Source from the catalog.
    - You already know the source_id (or the user/admin provided it, or you found it via search_source).

    Don't use when:
    - The claim is generic-pedagogic ("In general, SMEs..."). No source needed.
    - You don't know the source_id — call search_source first.
    - The source is not yet verified — flag_unsourced instead.
    """

    model_config = ConfigDict(extra="forbid")
    source_id: UUID
```

### Categorization

```python
TOOL_REGISTRY["cite_source"] = ToolDef(
    name="cite_source",
    schema=CiteSourceArgs,
    category=ToolCategory.READ,        # → DispatchCategory.REINVOKE_LLM
    requires_confirmation=False,
    description="Cite a verified source by source_id...",
)
```

### Handler contract

```python
# app/agent/handlers/cite_source.py
async def cite_source_handler(
    state: AgentState, call: ValidatedToolCall
) -> dict:
    """READ handler — returns serialized source metadata or structured error."""
    args: CiteSourceArgs = call.arguments  # already validated
    db: Session = ...  # injected
    src = db.query(Source).filter(Source.id == args.source_id).first()
    if src is None:
        return {
            "error": "source_not_found",
            "source_id": str(args.source_id),
            "hint": "use search_source to find a real source_id",
        }
    if src.verification_status != "verified":
        return {
            "error": "source_unverified",
            "source_id": str(args.source_id),
            "current_status": src.verification_status,
            "hint": "search_source for a verified alternative or flag_unsourced",
        }
    return {
        "source_id": str(src.id),
        "title": src.title,
        "publisher": src.publisher,
        "url": src.canonical_url or src.url,
        "page": src.page,
        "section": src.section,
        "version": src.version,
        "verification_status": "verified",
    }
```

### Status mapping (tool_call_log)

| Outcome           | tool_call_log.status |
|-------------------|----------------------|
| OK                | `ok`                 |
| Source not found  | `source_unverified`  |
| Source unverified | `source_unverified`  |

## Tool 2 — `search_source`

### Purpose

Discover verified Sources by semantic similarity to a free-text query. Uses Voyage `voyage-3.5` (1024 dim) and pgvector cosine search ; falls back to SQL `ILIKE` if Voyage is unavailable.

### Pydantic schema

```python
class SearchSourceArgs(BaseModel):
    """Arguments for the search_source tool.

    Use when:
    - You need to find a verified Source matching a topic (e.g., "GCF threshold for SMEs", "ADEME diesel emission factor").
    - You don't know the source_id ahead of time.

    Don't use when:
    - You already have the source_id — use cite_source directly.
    - The query is too generic ("ESG"). Be specific.
    """

    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)
```

### Categorization

```python
TOOL_REGISTRY["search_source"] = ToolDef(
    name="search_source",
    schema=SearchSourceArgs,
    category=ToolCategory.READ,        # → DispatchCategory.REINVOKE_LLM
    requires_confirmation=False,
    description="Search verified Sources by semantic similarity...",
)
```

### Handler contract

```python
async def search_source_handler(state, call) -> dict:
    args: SearchSourceArgs = call.arguments
    try:
        embedding = await voyage_client.embed(args.query, model="voyage-3.5")
        rows = db.execute(text("""
            SELECT id, title, publisher, url, page, section,
                   LEFT(notes, 200) AS snippet,
                   1 - (embedding <=> CAST(:e AS vector)) AS score
            FROM source
            WHERE verification_status = 'verified' AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:e AS vector) ASC
            LIMIT :limit
        """), {"e": embedding, "limit": args.limit}).mappings().all()
        return {"results": [dict(r) for r in rows], "degraded": False}
    except VoyageError:
        # Fallback ILIKE
        like_q = f"%{args.query}%"
        rows = db.execute(text("""
            SELECT id, title, publisher, url, page, section,
                   LEFT(notes, 200) AS snippet, NULL::float AS score
            FROM source
            WHERE verification_status = 'verified'
              AND (title ILIKE :q OR section ILIKE :q OR publisher ILIKE :q)
            ORDER BY length(title) ASC
            LIMIT :limit
        """), {"q": like_q, "limit": args.limit}).mappings().all()
        return {"results": [dict(r) for r in rows], "degraded": True}
```

### Output schema (informal)

```json
{
  "results": [
    {
      "id": "uuid",
      "title": "ADEME Base Carbone v23.5",
      "publisher": "ADEME",
      "url": "https://...",
      "page": "p.45",
      "section": "Diesel",
      "snippet": "Emission factor for diesel...",
      "score": 0.87
    }
  ],
  "degraded": false
}
```

## Tool 3 — `flag_unsourced`

### Purpose

Acknowledge that the LLM cannot source a particular claim, persisting it to the `unsourced_flag` table and emitting an SSE event so the user sees a transparency badge. The admin uses this backlog to prioritize new sources to add (F07).

### Pydantic schema

```python
class FlagUnsourcedArgs(BaseModel):
    """Arguments for the flag_unsourced tool.

    Use when:
    - You're about to make a factual claim (number, threshold, deadline) but no verified source exists in the catalog.
    - You'd rather be transparent than hallucinate.

    Don't use when:
    - You can cite a source — use cite_source instead.
    - The claim is generic-pedagogic — no flag needed.
    - The claim is from a tool output (e.g., "you have 3 active projects" from a DB read) — already from_tool=true.
    """

    model_config = ConfigDict(extra="forbid")
    claim: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=500)
```

### Categorization

```python
TOOL_REGISTRY["flag_unsourced"] = ToolDef(
    name="flag_unsourced",
    schema=FlagUnsourcedArgs,
    category=ToolCategory.MUTATION,    # → DispatchCategory.DB_MUTATION
    requires_confirmation=False,
    description="Flag a claim that cannot be sourced...",
)
```

### Handler contract

```python
async def flag_unsourced_handler(args: FlagUnsourcedArgs, ctx: MutationCtx) -> MutationResult:
    """MUTATION handler — INSERT unsourced_flag (ON CONFLICT DO NOTHING) + audit + SSE."""
    new_id = ctx.db.execute(text("""
        INSERT INTO unsourced_flag
            (id, account_id, user_id, agent_run_id, thread_id, message_id,
             claim, reason, source_of_change, created_at, updated_at, version)
        VALUES
            (gen_random_uuid(), :aid, :uid, :rid, :tid, :mid, :claim, :reason,
             'llm', now(), now(), 1)
        ON CONFLICT (account_id, thread_id, lower(claim)) WHERE resolved_at IS NULL
        DO NOTHING
        RETURNING id
    """), {...}).scalar()
    if new_id is None:
        # Existing duplicate — silent
        return MutationResult(entity_type="unsourced_flag", entity_id=None, fields_updated=[], snapshot=None, audit_log_id=None)
    audit_id = ctx.audit_logger(
        entity_type="unsourced_flag",
        entity_id=new_id,
        new={"claim": args.claim, "reason": args.reason},
        source_of_change="llm",
    )
    # Best-effort SSE emission
    await ctx.event_bus_publisher(
        ctx.account_id,
        "unsourced_claim",
        {"thread_id": str(thread_id), "message_id": str(message_id), "claim": args.claim, "reason": args.reason, "agent_run_id": str(ctx.agent_run_id)},
    )
    return MutationResult(
        entity_type="unsourced_flag",
        entity_id=new_id,
        fields_updated=["claim", "reason"],
        snapshot={"claim": args.claim, "reason": args.reason},
        audit_log_id=audit_id,
    )
```

### Auto-flag in permissive mode

When `LLM_AGENT_SOURCING_MODE=permissive` and the validator detects unsourced claims, the `compose_response` node calls `flag_unsourced_handler` directly (system-mode invocation, not through the LLM tool call), with :

```python
claim = first_unsourced_claim.raw  # Q4 — first detected
reason = f"auto_detected:{len(unsourced_claims)}_unsourced_claims"
```

The same dedup `ON CONFLICT DO NOTHING` applies.

## Cap on tool exposure (FR-008)

Per US1 / FR-008 :

```python
# app/agent/nodes/select_tools.py (modified)
SOURCING_FORCED = ("cite_source", "search_source", "flag_unsourced")

def node_select_tools(state):
    selected = ...  # F14 selector returns up to 10 tool names
    settings = get_settings()
    if settings.LLM_AGENT_SOURCING_MODE != "off":
        for t in SOURCING_FORCED:
            if t not in selected:
                selected.append(t)  # exposed beyond the 10-tool métier cap
    return {"available_tools": selected}
```

The `HARD_TOOL_CALLS_CAP=10` (F55) caps **invocations per turn**, not exposure. The 3 sourcing tools are exposed but only invoked when needed — the LLM rarely calls 13 tools in a single turn.

## Eval gating (FR-015)

The 3 tools are part of the LLM eval golden set :
- `tests/llm_eval/sourcing_eval.py` runs the 50-case golden against a small mock LLM (deterministic responses).
- CI gate : `recall ≥ 0.90`, `precision ≥ 0.85` for the detector ; `accept_rate ≥ 0.80`, `retry_rate ≤ 0.10` for the validator.

## OpenAPI fragment (for documentation)

```yaml
# Not exposed via REST — these are LLM tools, not HTTP endpoints.
# Documented here for tool-introspection by /admin/agent/tools (future endpoint).
openapi: 3.1.0
components:
  schemas:
    CiteSourceArgs:
      type: object
      required: [source_id]
      additionalProperties: false
      properties:
        source_id: {type: string, format: uuid}
    SearchSourceArgs:
      type: object
      required: [query]
      additionalProperties: false
      properties:
        query: {type: string, minLength: 1, maxLength: 500}
        limit: {type: integer, minimum: 1, maximum: 10, default: 5}
    FlagUnsourcedArgs:
      type: object
      required: [claim, reason]
      additionalProperties: false
      properties:
        claim: {type: string, minLength: 1, maxLength: 1000}
        reason: {type: string, minLength: 1, maxLength: 500}
```
