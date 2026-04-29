# Manual Tests — F17 Tools de Mutation LLM

**Date**: 2026-04-29
**Branch**: `017-tools-mutation-llm`

## Tests automatisés (pytest)

```
$ pytest -q tests/orchestrator/tools/mutations/
59 passed in <1s

$ pytest -q --cov=app/orchestrator/tools/mutations \
    tests/orchestrator/tools/mutations/
Coverage: 99.11%
- __init__.py                  100%
- _destructive.py              100%
- _rate_limit.py               100%
- create_project.py            100%
- delete_project.py            100%
- update_company_profile.py    100%
- update_project.py             96%

$ ruff check app/orchestrator/tools/mutations/ \
    tests/orchestrator/tools/mutations/
All checks passed!

$ pytest -q tests/orchestrator/ tests/tools/
224 passed (no regression on F14-F16)
```

## Couverture des Success Criteria (P1)

| SC | Test |
|-|-|
| SC-001 (P1) | `test_register_adds_tool` x4 + handler tests sur les 4 tools |
| SC-002 (delete sans confirmation) | `test_delete_project::test_blocks_without_confirmation` |
| SC-005 (registry sans catalogue) | `test_registry_no_catalog` (24 mutations interdites) |
| SC-007 (100% audit) | Tests vérifient `source_of_change == LLM` (audit délégué à F11/F12 déjà testés) |
| FR-002 (@destructive) | `test_destructive` (6 cas) |
| FR-007 (Pydantic strict) | `test_extra_field_rejected`, `test_unknown_field_rejected`, `test_iso2_length_validated`, ... |
| FR-010 (rate limit 10/min) | `test_rate_limit` (5 cas) |

## Scope livré

**P1 livré** :
- Décorateur `@destructive` + `MutationConfirmationRequired` (FR-002, NFR-003)
- Décorateur `@rate_limited(max_per_min=10)` + `RateLimitExceeded` (FR-010)
- Tool `update_company_profile` (US1) → `entreprise.service.update_partial(LLM)`
- Tool `create_project` (US2) → `projets.service.create_projet(LLM)`
- Tool `update_project` (US2) → `projets.service.patch_projet(LLM)`
- Tool `delete_project` (US2 + US4 destructif) → `projets.service.delete_projet(LLM)`
- `register_mutation_tools()` n'enregistre que ces 4 tools (FR-009)

**[DEFERRED]** :
- US3 candidatures CRUD — pas de service `create/update/delete_candidature` côté backend, à créer dans une feature dédiée.
- US6-US10 (P2) : `attach_document` (dépend F22), `recompute_score` (F23), `generate_attestation`/`revoke_attestation` (F30), `generate_dossier` (F26), endpoint UNDO `POST /me/audit-log/{id}/revert`.
- HTTP route `POST /me/llm-tools/mutations/{name}` (Phase 6) — invocation passe par F14 LangGraph en MVP.
- Test cross-tenant (T015) — couvert par tests F11/F12 RLS existants.

## Observations

- Les services F11/F12 émettent déjà l'audit log (`source_of_change=LLM`) et l'EventBus, donc F17 reste un layer mince.
- La validation Pydantic stricte (`extra='forbid'`) est imposée par le `tool()` registrar de F14.
- Aucune migration Alembic nécessaire.

## Ready for PR

Oui — livraison partielle MVP P1 avec `scope_partial=true` (US3 + US6-US10 deferrés).
