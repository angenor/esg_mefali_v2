"""F56 — Pydantic schemas for the 3 sourcing tools (FR-003, FR-004, FR-005).

All schemas use ``model_config = ConfigDict(extra='forbid')`` per P9
(Tool-use LLM fiable). Bounded fields enforce DOS limits.

Reference : ``contracts/tool-registry.md``.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CiteSourceArgs(BaseModel):
    """Arguments for the ``cite_source`` tool.

    Use when:
    - You need to back a factual claim (number, threshold, formula,
      reference) with a verified Source from the catalog.
    - You already know the source_id (or you found it via search_source).

    Don't use when:
    - The claim is generic-pedagogic ("In general, SMEs..."). No source needed.
    - You don't know the source_id — call search_source first.
    - The source is not yet verified — flag_unsourced instead.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: UUID


class SearchSourceArgs(BaseModel):
    """Arguments for the ``search_source`` tool.

    Use when:
    - You need to find a verified Source matching a topic
      (e.g., "GCF threshold for SMEs", "ADEME diesel emission factor").
    - You don't know the source_id ahead of time.

    Don't use when:
    - You already have the source_id — use cite_source directly.
    - The query is too generic ("ESG"). Be specific.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


class FlagUnsourcedArgs(BaseModel):
    """Arguments for the ``flag_unsourced`` tool.

    Use when:
    - You're about to make a factual claim (number, threshold, deadline) but
      no verified source exists in the catalog.
    - You'd rather be transparent than hallucinate.

    Don't use when:
    - You can cite a source — use cite_source instead.
    - The claim is generic-pedagogic — no flag needed.
    - The claim is from a tool output (e.g., "you have 3 active projects"
      from a DB read) — already from_tool=true.
    """

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=500)


__all__ = [
    "CiteSourceArgs",
    "FlagUnsourcedArgs",
    "SearchSourceArgs",
]
