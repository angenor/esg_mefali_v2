"""F56 — Pydantic / dataclass models for sourcing enforcement.

Reference :
- ``specs/056-agent-sourcing-enforcement/data-model.md`` §5
- ``specs/056-agent-sourcing-enforcement/contracts/sourcing-validator.md``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ClaimKind = Literal[
    "number_with_unit",
    "percentage",
    "ratio",
    "range",
    "reference_keyword",
    "threshold",
    "formula",
]
"""7 categories of factual claim handled by the detector (FR-001)."""

SourcingMode = Literal["strict", "permissive", "off"]
"""``LLM_AGENT_SOURCING_MODE`` runtime value (FR-007)."""

SourcingDecision = Literal["accept", "retry", "fallback", "annotate"]
"""Validator decision (FR-002)."""


# ---------------------------------------------------------------------------
# Claim — emitted by the detector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Claim:
    """Detected factual claim in an assistant message text.

    Frozen dataclass (immutable per coding-style P1).

    Attributes:
        span: ``(start, end)`` character offsets in the original text.
        kind: One of ``ClaimKind``.
        raw: The matched substring (already extracted from text).
        from_tool: ``True`` if the same substring appears in any
            ``tool_outputs`` of the current turn (FR-001 — claim is provided
            by a tool, not invented by the LLM).
    """

    span: tuple[int, int]
    kind: ClaimKind
    raw: str
    from_tool: bool = False


# ---------------------------------------------------------------------------
# CitationRef / SourceRef / SourcingValidationResult
# ---------------------------------------------------------------------------


class CitationRef(BaseModel):
    """A ``cite_source`` invocation observed in the turn.

    Tracks which paragraph the citation covers (paragraph-level granularity,
    cf. ``contracts/sourcing-validator.md`` Algorithm).
    """

    model_config = ConfigDict(extra="forbid")

    tool_call_id: str
    source_id: UUID
    paragraph_index: int = Field(ge=-1)


class SourcingValidationResult(BaseModel):
    """Output of ``validate_response``.

    Reference: ``contracts/sourcing-validator.md`` §Result schema.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    claims_detected: list[Claim] = Field(default_factory=list)
    citations_found: list[CitationRef] = Field(default_factory=list)
    unsourced_claims: list[Claim] = Field(default_factory=list)
    mode: SourcingMode
    decision: SourcingDecision
    duration_ms: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# SourceRef — written to ``chat_message.sources`` and ``message_done.sources``
# ---------------------------------------------------------------------------


class SourceRef(BaseModel):
    """Aggregated reference to a verified source cited in a message.

    Reference: ``contracts/sse-events.md`` §SourceRef.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    title: str
    publisher: str
    url: str
    page: str | None = None
    section: str | None = None
    verification_status: Literal["verified", "outdated"] = "verified"
    version: str | None = None
    citation_index: int = Field(ge=1)
    spans: list[tuple[int, int]] = Field(default_factory=list)


__all__ = [
    "CitationRef",
    "Claim",
    "ClaimKind",
    "SourceRef",
    "SourcingDecision",
    "SourcingMode",
    "SourcingValidationResult",
]
