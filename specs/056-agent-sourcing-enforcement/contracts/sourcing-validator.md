# Contract — Sourcing Validator (FR-002)

**Status**: Phase 1 (canonical)

## Public API

### `app/agent/sourcing/detector.py`

```python
from dataclasses import dataclass
from typing import Literal

ClaimKind = Literal[
    "number_with_unit", "percentage", "ratio", "range",
    "reference_keyword", "threshold", "formula",
]

@dataclass(frozen=True)
class Claim:
    span: tuple[int, int]   # (start, end) char offsets
    kind: ClaimKind
    raw: str                # the matched substring
    from_tool: bool = False # True if matched in tool_outputs


def detect_claims(
    text: str,
    *,
    tool_outputs: list[str] | None = None,
) -> list[Claim]:
    """Detect factual claims in `text`.

    Args:
        text: The assistant message text (FR; EN post-MVP).
        tool_outputs: Concatenated stringified outputs from tool_message of the
            current turn. Substring matches mark claims as ``from_tool=True``
            (excluded from validation per FR-001).

    Returns:
        list[Claim] — sorted by span start, deduplicated by exact span overlap.

    Performance:
        < 50 ms p95 for 2 KB text (NFR-001).

    Notes:
        - Whitelist patterns (``app/agent/sourcing/whitelist.py``) are checked
          per-sentence; whitelisted sentences are skipped entirely (no claim
          extraction within).
        - Synchronous, no LLM dependency (NFR-005).
    """
```

### `app/agent/sourcing/whitelist.py`

```python
WHITELIST_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\bEn général,?\b", re.I),
    re.compile(r"\bCela dépend de\b", re.I),
    re.compile(r"\bTypiquement,?\b", re.I),
    # ... 20-30 total
)

def is_whitelisted(sentence: str) -> bool:
    """True iff any WHITELIST_PATTERNS matches the sentence."""
```

### `app/agent/sourcing/validator.py`

```python
from pydantic import BaseModel, ConfigDict
from app.agent.sourcing.detector import Claim
from app.agent.sourcing.models import (
    CitationRef, SourcingValidationResult, SourcingMode, SourcingDecision,
)
from app.agent.state import ValidatedToolCall


def validate_response(
    response_text: str,
    tool_calls: list[ValidatedToolCall],
    *,
    tool_outputs: list[str] | None = None,
    mode: SourcingMode = "strict",
    sourcing_retry_count: int = 0,
) -> SourcingValidationResult:
    """Cross-reference detected claims with cite_source invocations.

    Args:
        response_text: The text content of the assistant final message.
        tool_calls: All ValidatedToolCall of the current turn (we filter for
            ``cite_source`` and use their paragraph positions).
        tool_outputs: Outputs of tool_message of the current turn (read tools
            etc.) — used to mark claims as ``from_tool=True``.
        mode: ``strict`` | ``permissive`` | ``off``.
        sourcing_retry_count: 0 on first pass, 1 if this is the retry pass.

    Returns:
        SourcingValidationResult with decision:
        - ``accept``  — no unsourced claims, or mode != strict.
        - ``retry``   — strict mode, ≥1 unsourced claim, retry_count == 0.
        - ``fallback``— strict mode, ≥1 unsourced claim, retry_count >= 1.
        - ``annotate``— permissive mode, ≥1 unsourced claim.

    Performance:
        < 100 ms p95 (NFR-008).

    Notes:
        - Cross-reference granularity = paragraph (R2 research).
        - Whitelist hits never appear in claims_detected.
        - from_tool=true claims are excluded from unsourced_claims.
    """
```

### Result schema

```python
class CitationRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_call_id: str
    source_id: UUID
    paragraph_index: int  # 0-based; -1 if invocation precedes any paragraph

class SourcingValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims_detected: list[Claim]
    citations_found: list[CitationRef]
    unsourced_claims: list[Claim]
    mode: SourcingMode
    decision: SourcingDecision
    duration_ms: int
```

## Algorithm

```text
1. paragraphs = response_text.split("\n\n")
2. paragraph_offsets = build (start, end) per paragraph
3. claims = detect_claims(response_text, tool_outputs=tool_outputs)
4. claims = filter(c -> not c.from_tool, claims)
5. cite_calls = filter(call.name == "cite_source", tool_calls)
6. paragraph_has_citation = compute mapping paragraph_index -> bool
   (a cite_source whose paragraph_index <= p covers paragraph p — paragraph-level)
7. unsourced = []
   for claim in claims:
     pi = paragraph_index_of(claim.span[0], paragraph_offsets)
     if not paragraph_has_citation[pi]:
       unsourced.append(claim)
8. decision:
   if mode == "off": decision = "accept"  (and the validator doesn't run normally; defensive)
   elif not unsourced: decision = "accept"
   elif mode == "permissive": decision = "annotate"
   elif mode == "strict" and sourcing_retry_count == 0: decision = "retry"
   else: decision = "fallback"
9. return SourcingValidationResult(...)
```

### Paragraph index of cite_source

The LLM is instructed (via system prompt F54) to invoke `cite_source` immediately after a paragraph containing a claim. The paragraph_index of a `cite_source` is the paragraph index at the time of invocation — encoded by the order of tool_calls in the turn :

- The LLM emits tokens sequentially. We track the current paragraph by counting `\n\n` boundaries crossed up to each tool_call_id boundary (recorded in F53 token streaming).
- For MVP, we approximate: a `cite_source` "covers" paragraph p iff the call appears in the tool_calls list AND the paragraph_index of the call ≤ p. The tool_calls are time-ordered; we approximate that the i-th cite_source covers from paragraph i-1 to ∞ (cumulative coverage). Refinement post-MVP.

This approximation is acceptable for MVP because :
- LLM typically emits 1-3 paragraphs per response.
- Eval golden set (FR-015) tests this approximation.

## Logging (FR-016)

```python
logger.info(
    "sourcing_check",
    extra={
        "agent_run_id": str(state.agent_run_id),
        "claims_detected": len(result.claims_detected),
        "citations_found": len(result.citations_found),
        "unsourced_count": len(result.unsourced_claims),
        "mode": result.mode,
        "retried": sourcing_retry_count > 0,
        "decision": result.decision,
        "duration_ms": result.duration_ms,
    },
)
```

## Integration into `compose_response` (FR-008..010)

```python
# app/agent/nodes/compose_response.py (additions)
async def node_compose_response(state):
    # ... existing F53 logic produces final assistant message text ...
    settings = get_settings()
    mode = settings.LLM_AGENT_SOURCING_MODE
    if mode == "off":
        return {...}  # existing behavior

    tool_outputs = collect_tool_outputs(state)
    result = validate_response(
        text, state.tool_calls_made_in_turn,
        tool_outputs=tool_outputs, mode=mode,
        sourcing_retry_count=state.sourcing_retry_count,
    )
    log_structured("sourcing_check", result)

    if result.decision == "retry":
        # FR-008: trigger 1 retry
        retry_msg = build_sourcing_retry_message(result.unsourced_claims)
        return {
            "messages": [retry_msg],          # appended via _append reducer
            "sourcing_retry_count": 1,        # _max reducer
            "sourcing_decision": "retry",
            "next_node": "call_llm",          # graph router will see the retry
        }

    if result.decision == "fallback":
        # FR-009/010
        truncated_or_substituted = truncate_to_last_sourced_paragraph(text, result)
        return {
            "messages": [AIMessage(content=truncated_or_substituted)],
            "sourcing_decision": "fallback",
            "agent_run_status_patch": {"sourcing_status": "failed"},
        }

    if result.decision == "annotate":
        # FR-permissive auto-flag (Q4 rollup)
        await auto_flag_unsourced_rollup(state, result)
        return {
            "messages": [AIMessage(content=text)],
            "sourcing_decision": "annotate",
        }

    # decision == "accept"
    sources = aggregate_sources_from_calls(state.tool_calls_made_in_turn, result)
    return {
        "messages": [AIMessage(content=text)],
        "sourcing_decision": "accept",
        "message_sources_patch": sources,    # written to chat_message.sources
        "agent_run_status_patch": {"sourcing_status": "ok" if state.sourcing_retry_count == 0 else "retried_ok"},
    }
```

## Test contracts

### Unit tests (mandatory)

- `test_sourcing_detector.py` :
  - Each ClaimKind has ≥ 3 positive cases.
  - `from_tool=True` correctly set when text matches tool_outputs.
  - Whitelist hit returns empty list for whitelisted sentence.
  - Performance: < 50 ms for 2000 chars (perf marker).

- `test_sourcing_validator.py` :
  - All 4 decisions tested (accept, retry, fallback, annotate).
  - Mode `off` short-circuits.
  - Paragraph coverage : claim in p2 + cite_source for p1 → covered (cumulative).
  - Unsourced claim with retry_count==1 → fallback.

- `test_sourcing_whitelist.py` :
  - All 20+ patterns tested (positive + negative).
  - Specific claims like "Le seuil de 50 M USD" NOT whitelisted by "En général" pattern.

### Integration tests

- `test_compose_response_retry.py` : full agent run with mocked LLM, 3 modes.
- `test_sourcing_e2e_strict.py` : real DB + mocked LLM ; strict mode rejects → retry → accept OR fallback.

### Golden test (FR-015 / NFR-003)

- `test_sourcing_golden.py` (or pytest target `eval_sourcing_golden`) : runs 50-case `tests/golden/sourcing.jsonl` ; computes precision/recall ; CI fails if below thresholds.
