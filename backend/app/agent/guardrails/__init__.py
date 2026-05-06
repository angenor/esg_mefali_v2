"""F58 — Agent guardrails sub-package.

Layered protection plane for the LangGraph agent assembled by F53–F57:

- :mod:`anti_injection` — detect canonical prompt-injection patterns (FR-001/2).
- :mod:`pii_patterns` / :mod:`pii_detector` — mask UEMOA PII before persistence
  (FR-003/4).
- :mod:`lang_check` — language detection + retry FR (FR-005/6).
- :mod:`circuit_breaker` — in-memory per-worker LLM circuit breaker (FR-010/11).
- :mod:`budget` — daily token sub-quotas + per-turn cap (FR-012-15).
- :mod:`tool_status` — admin kill-switch repository + cache (FR-007-9).
- :mod:`loop_detector` — detect tool-call loops (FR-016).

All modules expose pure functions where possible; stateful pieces
(``CircuitBreaker``, ``tool_status`` cache) are encapsulated singletons.
"""

from __future__ import annotations

__all__: list[str] = []
