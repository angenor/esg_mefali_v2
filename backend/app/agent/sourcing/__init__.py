"""F56 — Sourcing enforcement package.

Three lines of defense for the constitutional invariant **P1**
(every factual ESG/financial claim must point to a verified ``Source``) :

1. **Before** — system prompt instructs the LLM to cite (F54).
2. **During** — the 3 sourcing tools (``cite_source``, ``search_source``,
   ``flag_unsourced``) are always exposed via ``select_tools`` (US1).
3. **After** — the detector + validator scan the assistant text and apply
   the configured policy (``strict`` | ``permissive`` | ``off``).

Pure-logic package : no DB access. Database calls happen inside handlers
(``app.agent.handlers.cite_source``, ``search_source``, ``flag_unsourced``).
"""

from __future__ import annotations

from app.agent.sourcing.models import (
    CitationRef,
    Claim,
    ClaimKind,
    SourceRef,
    SourcingDecision,
    SourcingMode,
    SourcingValidationResult,
)

__all__ = [
    "CitationRef",
    "Claim",
    "ClaimKind",
    "SourceRef",
    "SourcingDecision",
    "SourcingMode",
    "SourcingValidationResult",
]
