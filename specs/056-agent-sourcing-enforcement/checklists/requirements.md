# Specification Quality Checklist: Agent Sourcing Enforcement (F56)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)  *(stack mentioned in dependencies/assumptions only — necessary because this is a backend agent feature with strict invariants)*
- [x] Focused on user value and business needs  *(P1 traceability is the competitive promise to fund officers)*
- [x] Written for non-technical stakeholders (US/SC sections)
- [x] All mandatory sections completed (User Scenarios, Requirements, Success Criteria)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous (FR-001..FR-021 each map to a verifiable behavior)
- [x] Success criteria are measurable (SC-001..SC-012 with thresholds and rates)
- [x] Success criteria are technology-agnostic where possible (latency, recall/precision, compliance rate)
- [x] All acceptance scenarios are defined (Given/When/Then per US)
- [x] Edge cases are identified (Hallucination source_id, Voyage down, cold cache, tool outputs, mode off in prod, etc.)
- [x] Scope is clearly bounded (Hors-scope MVP explicit)
- [x] Dependencies and assumptions identified (F03, F07, F35, F53, F54, F55, Voyage, pgvector)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (US1-US10, P1 priority for the 8 critical ones)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification (Pydantic/SQL details limited to FR for testability)

## Constitutional Alignment (Module 0)

- [x] **P1 Sourcing** : core enforcement mechanism (this is THE feature)
- [x] **P2 RLS** : `unsourced_flag` scoped `account_id`
- [x] **P3 Audit append-only** : `unsourced_flag` policy noted
- [x] **P4 Versioning** : N/A (no referential changes here)
- [x] **P5 Money typed** : N/A
- [x] **P6 Indicateur pivot** : N/A
- [x] **P7 PME/Admin** : metrics endpoint admin-gated
- [x] **P8 Sync DB↔LLM** : `chat_message.sources` is DB source of truth
- [x] **P9 Tool-use Pydantic strict** : 3 new tools with `extra='forbid'`
- [x] **P10 UI bottom sheet** : N/A (backend post-processing + inline chips, no interactive input)

## Notes

- All functional requirements (FR-001..FR-021) trace to one or more User Stories.
- Success Criteria SC-010 enforces golden set quality (recall ≥ 0.90, precision ≥ 0.85) — gating CI.
- Risks documented with mitigations for top 7 issues.
- `LLM_AGENT_SOURCING_MODE=off` forbidden in production via fail-fast config check (FR-007).
- This spec is ready for `/speckit-clarify`.
