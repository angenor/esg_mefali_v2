# Tasks: F14 — LangGraph Routing & Pydantic Validation Pipeline

**Feature**: `014-langgraph-routing-validation`
**Input docs**: spec.md, plan.md, research.md, data-model.md, contracts/sse-events-f14.md, quickstart.md

Approche : TDD strict (RED → GREEN → REFACTOR). Couverture ≥ 80 % sur `backend/app/orchestrator/`. Lint ruff vert.
Marqueur `[P]` = parallélisable (fichiers indépendants, pas de dépendance sur tâche en cours).

> **Phase B — Statut : MVP partiel livré (2026-04-29).**
>
> **Livrés (US4, US6, US7, US2, US3 — règles MVP)** : tool registry, payload validator Pydantic, retry policy avec fallback texte, intent classifier rule-based avec cache TTL, tool selector borné MAX_TOOLS=10 + whitelist Skills, 5 tools fictifs en fixture, schémas Pydantic stricts (`extra='forbid'`).
>
> Couverture `app/orchestrator/` : **98.31 %** (39 tests verts, ruff clean).
>
> **Différés `[DEFERRED]`** : T010-T013 migration Alembic + ORM `tool_call_log`, T050-T051 system prompt builder (US5), T080-T083 thread lock + pipeline E2E (US1), T090-T092 streaming SSE F14 (US8), T100-T104 logging persistance + admin read (US9), T110-T115 polish & non-régression complète. Fallback LLM du classifier (US2 "voie LLM légère") également différé — règles seulement en MVP.
>
> Raison du report : gate fact-forcing systématique + budget contextuel. Le socle livré (registry + validator + retry + classifier + selector) est complet et testable indépendamment ; le pipeline `respond()` end-to-end et l'intégration `chat/llm_stream.py` restent à câbler dans une itération suivante.

---

## Phase 1 — Setup

- [x] T001 Branche vérifiée : `014-langgraph-routing-validation`.
- [x] T002 Pas de `cachetools` requis : cache TTL maison `dict + time.monotonic()`.
- [x] T003 [P] `backend/app/orchestrator/` peuplé (schemas, registry, validator, retry, classifier, selector, fixtures).
- [x] T004 [P] `backend/tests/orchestrator/` créé avec `__init__.py` + `conftest.py` (autouse `reset_registry`).

## Phase 2 — Foundational (bloquant US1+)

- [ ] [DEFERRED] T010 Test Alembic `tool_call_log`.
- [ ] [DEFERRED] T011 Migration Alembic `tool_call_log` + RLS.
- [ ] [DEFERRED] T012 [P] Test ORM `tool_call_log`.
- [ ] [DEFERRED] T013 ORM `app/models/tool_call_log.py`.
- [x] T014 [P] `app/orchestrator/schemas.py` : `ToolCallStatus`, `Intent`, `ValidationErrorDetail`, `ToolCallResult`, `PipelineResponse` (tous `extra='forbid'`). Note : `ToolCallLogCreate/Read` reportés avec la migration.

## Phase 3 — User Story 4 : Tool registry (P1, fondation pour US1/US3/US5/US6/US7)

**Goal** : convention `@tool` unique, registry global, schémas stricts.
**Independent test** : 5 tools fictifs déclarés sont introspectables, leurs schémas rejettent `extra` fields.

- [x] T020 [P] [US4] `test_tool_registry.py` : registre, doublon `ValueError`, schéma lax `ValueError`, fixtures.
- [x] T021 [US4] `tool_registry.py` : `ToolDef` dataclass frozen, helper `tool(...)`, `TOOL_REGISTRY`, `get_tool`, `UnknownToolError`, `reset_registry`.
- [x] T022 [US4] `fixtures_tools.py` : 5 tools (`show_summary_card`, `ask_qcu`, `ask_yes_no`, `update_demo_profile`, `search_demo_source`).
- [x] T023 [US4] Assertions sur les 5 tools dans `test_tool_registry.py`.

## Phase 4 — User Story 2 : Intent classifier (P1)

**Goal** : règles + fallback LLM + cache TTL ; 7 intentions.
**Independent test** : 30 messages → ≥ 90 % d'intention attendue.

- [x] T030 [P] [US2] `test_intent_classifier.py` : 12 cas paramétrés règles + fallback `autre` + cache thread-isolation + cache hit. **Note** : couvre les 7 intentions ; les 30 cas exhaustifs et le fallback LLM sont [DEFERRED].
- [x] T031 [US2] `intent_classifier.py` : `Intent` Literal, `_RULES` FR mots-clés ordonnées, `classify(...)`, cache TTL `dict + time.monotonic()` (600 s). **[DEFERRED]** : voie LLM légère (T031b à créer).

## Phase 5 — User Story 3 : Tool selector (P1)

**Goal** : 5–10 tools max selon intention + page + skills ; defaults minimaux ; whitelist.
**Independent test** : 10 paires (intent, ctx) → set ≤ 10, jamais vide.

- [x] T040 [P] [US3] `test_tool_selector.py` : règles mutation/aide/all-intents, `MAX_TOOLS=10`, whitelist filtrage, fallback DEFAULT, jamais vide.
- [x] T041 [US3] `tool_selector.py` : `_BY_INTENT` mapping, `MAX_TOOLS=10`, `DEFAULT_TOOLS=("ask_qcu","ask_yes_no")`, intersection whitelist + fallback DEFAULT.

## Phase 6 — User Story 5 : System prompt builder (P1)

**Goal** : invariants + arbre décision + tools + contexte ; ≤ 4000 tokens ; alarme + troncature.
**Independent test** : prompt déterministe, plafond respecté.

- [ ] [DEFERRED] T050 [P] [US5] Tests system prompt builder.
- [ ] [DEFERRED] T051 [US5] `system_prompt_builder.py`.

## Phase 7 — User Story 6 : Payload validator (P1)

**Goal** : validation Pydantic stricte ; erreur structurée.
**Independent test** : 5 payloads malformés rejetés (SC-002).

- [x] T060 [P] [US6] `test_payload_validator.py` : extra-field, missing, wrong-type, enum, unknown-tool, format_for_llm.
- [x] T061 [US6] `payload_validator.py` : `validate(tool_name, payload) -> (ok, errors)`, mapping `ValidationError` → `ValidationErrorDetail`, `format_for_llm`.

## Phase 8 — User Story 7 : Retry policy (P1)

**Goal** : max 2 retries ; fallback texte ; tokens retry séparés.
**Independent test** : 2 invalides + 1 valide → exécuté ; toujours invalide → fallback (SC-003).

- [x] T070 [P] [US7] `test_retry_policy.py` : `decide(0/1)=retry`, `decide(MAX)=fallback`, `MAX_RETRIES=2`, `build_retry_prompt`.
- [x] T071 [US7] `retry_policy.py` : `MAX_RETRIES=2`, `decide(retry_count)`, `build_retry_prompt`, `FALLBACK_TEXT`.

## Phase 9 — User Story 1 + Edge cases : Pipeline + thread lock (P1)

**Goal** : `respond()` end-to-end ; sérialisation par thread_id (FR-016).
**Independent test** : 10 cas E2E ; 2 requêtes concurrentes même thread → sérialisées (SC-001, SC-009).

- [ ] [DEFERRED] T080 [P] [US1] Tests thread lock.
- [ ] [DEFERRED] T081 [US1] `thread_lock.py`.
- [ ] [DEFERRED] T082 [US1] Tests pipeline E2E.
- [ ] [DEFERRED] T083 [US1] `pipeline.py` `async def respond(...)`.

## Phase 10 — User Story 8 : Streaming SSE F14 events (P2)

**Goal** : 4+ events `thinking/tool_call_*` cohérents (SC-004).
**Independent test** : message → events dans l'ordre.

- [ ] [DEFERRED] T090 [P] [US8] Tests SSE pipeline.
- [ ] [DEFERRED] T091 [US8] Modifier `chat/llm_stream.py` (feature flag `F14_PIPELINE_ENABLED`).
- [ ] [DEFERRED] T092 [US8] Modifier `chat/api.py` (callback SSE).

## Phase 11 — User Story 9 : Logging append-only + admin read (P2)

**Goal** : 100 % des appels journalisés ; isolation tenant (SC-005).
**Independent test** : 10 appels → 10 lignes ; lecture admin filtrée par account_id.

- [ ] [DEFERRED] T100 [P] [US9] Tests log persistance.
- [ ] [DEFERRED] T101 [US9] `log_repository.py`.
- [ ] [DEFERRED] T102 [P] [US9] Tests admin endpoint.
- [ ] [DEFERRED] T103 [US9] `admin/tool_call_logs.py`.
- [ ] [DEFERRED] T104 [US9] Brancher router dans `main.py`.

## Phase 12 — Polish & validation finale

- [x] T110 `pytest tests/orchestrator/` : 39 passed, 98.31 % couverture.
- [x] T111 `--cov=app/orchestrator/` = 98.31 % (≥ 80 %).
- [x] T112 `ruff check app/orchestrator tests/orchestrator` : All checks passed.
- [ ] [DEFERRED] T113 [P] Non-régression F01-F13 complète : pré-existants 76 failed/98 errors liés à env DB sans migrations (non liés à F14).
- [x] T114 [P] `.cc-runtime/logs/manual-tests-14.md` créé.
- [ ] [DEFERRED] T115 Non-régression contrat F13 (à valider quand pipeline E2E sera câblé).

---

## Dépendances entre user stories

```
Phase 1 (Setup)
    └─> Phase 2 (Foundational : migration + ORM + schemas)
            └─> Phase 3 (US4 — tool registry)
                    ├─> Phase 4 (US2)  ┐
                    ├─> Phase 5 (US3)  │
                    ├─> Phase 6 (US5)  │  parallèles
                    ├─> Phase 7 (US6)  │
                    └─> Phase 8 (US7)  ┘
                            └─> Phase 9 (US1 — pipeline E2E)
                                    ├─> Phase 10 (US8 — SSE)
                                    └─> Phase 11 (US9 — log + admin)
                                            └─> Phase 12 (Polish)
```

US4 est la fondation. US2/US3/US5/US6/US7 peuvent avancer en parallèle après US4. US1 dépend de toutes les briques. US8/US9 sont des cross-cutting après US1.

## MVP scope suggéré

- **Tier 1 (obligatoire MVP)** : Phases 1, 2, 3 (US4), 4 (US2), 5 (US3), 6 (US5), 7 (US6), 8 (US7), 9 (US1) → pipeline complet + log basique inline. **Couverture ≥ 80 %**.
- **Tier 2 (DEFERRED si scope tendu)** : Phase 10 (US8 — streaming SSE riche) + Phase 11 (US9 — admin endpoint lecture). L'insertion de log reste obligatoire (intégrée dans Phase 9).

## Format validation

Tous les tasks suivent : `- [ ] Txxx [P?] [USx?] Description avec chemin`.
