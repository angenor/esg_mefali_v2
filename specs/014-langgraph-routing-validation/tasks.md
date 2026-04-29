# Tasks: F14 — LangGraph Routing & Pydantic Validation Pipeline

**Feature**: `014-langgraph-routing-validation`
**Input docs**: spec.md, plan.md, research.md, data-model.md, contracts/sse-events-f14.md, quickstart.md

Approche : TDD strict (RED → GREEN → REFACTOR). Couverture ≥ 80 % sur `backend/app/orchestrator/`. Lint ruff vert.
Marqueur `[P]` = parallélisable (fichiers indépendants, pas de dépendance sur tâche en cours).

> **[DEFERRED — implémentation Phase B]**
>
> La spec / plan / tasks (Phase A) ont été générés et commités sur la branche `014-langgraph-routing-validation` (commit spec). L'implémentation effective des tâches T001–T115 (Phase B) est **différée à une session ultérieure** : le volume (49 tâches, ≥ 8 nouveaux modules + migration + ORM + tests TDD + intégration chat API + endpoint admin + vérif non-régression F01–F13) dépasse le budget contextuel d'une session unique avec gate fact-forcing systématique sur chaque écriture.
>
> Tous les artefacts (spec.md, plan.md, research.md, data-model.md, contracts/sse-events-f14.md, quickstart.md, tasks.md) sont **prêts pour `/speckit-implement`** dans une session dédiée. Le contrat est figé : aucune ré-clarification nécessaire.
>
> Préfixer toutes les tâches de Phase B suivantes par `[DEFERRED]`.

---

## Phase 1 — Setup

- [ ] T001 Vérifier la branche : `git branch --show-current` doit afficher `014-langgraph-routing-validation`.
- [ ] T002 Vérifier que `cachetools` est dispo dans `backend/.venv` ; si manquant, traiter en T002b (sinon `pyproject.toml` est zone interdite — utiliser `dict + time.monotonic()` interne en remplacement).
- [ ] T003 [P] Créer la structure `backend/app/orchestrator/` (vide avec `__init__.py`).
- [ ] T004 [P] Créer la structure `backend/tests/orchestrator/` (vide avec `__init__.py` + `conftest.py` minimal).

## Phase 2 — Foundational (bloquant US1+)

- [ ] T010 Écrire le test Alembic (RED) `backend/tests/orchestrator/test_migration_tool_call_log.py` qui vérifie : table créée, colonnes correctes, index ×3, RLS active, contrainte CHECK status, append-only.
- [ ] T011 Implémenter la migration Alembic `backend/alembic/versions/20260429_xxxx_add_tool_call_log.py` : `create_table tool_call_log`, 3 index, `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`, `CREATE POLICY tool_call_log_tenant_isolation`. Lancer `alembic upgrade head` ; T010 doit passer (GREEN).
- [ ] T012 [P] Écrire test ORM `backend/tests/orchestrator/test_model_tool_call_log.py` (insertion, lecture par account_id, defaults).
- [ ] T013 Implémenter `backend/app/models/tool_call_log.py` (SQLAlchemy ORM `ToolCallLog`).
- [ ] T014 [P] Écrire `backend/app/orchestrator/schemas.py` (Pydantic `ToolCallStatus`, `ValidationErrorDetail`, `ToolCallLogCreate`, `ToolCallLogRead` ; tous `extra='forbid'`).

## Phase 3 — User Story 4 : Tool registry (P1, fondation pour US1/US3/US5/US6/US7)

**Goal** : convention `@tool` unique, registry global, schémas stricts.
**Independent test** : 5 tools fictifs déclarés sont introspectables, leurs schémas rejettent `extra` fields.

- [ ] T020 [P] [US4] Écrire `backend/tests/orchestrator/test_tool_registry.py` (RED) : `@tool` enregistre dans `TOOL_REGISTRY` ; doublon `name` lève `ValueError` ; chaque tool fictif a `extra='forbid'`.
- [ ] T021 [US4] Implémenter `backend/app/orchestrator/tool_registry.py` : dataclass `ToolDef`, decorator `@tool`, dict `TOOL_REGISTRY`, helper `get_tool(name)`. (GREEN T020).
- [ ] T022 [US4] Implémenter `backend/app/orchestrator/fixtures_tools.py` : 5 tools fictifs (`show_summary_card`, `ask_qcu`, `ask_yes_no`, `update_demo_profile`, `search_demo_source`).
- [ ] T023 [US4] Compléter `backend/tests/orchestrator/test_tool_registry.py` avec assertions sur les 5 tools fictifs.

## Phase 4 — User Story 2 : Intent classifier (P1)

**Goal** : règles + fallback LLM + cache TTL ; 7 intentions.
**Independent test** : 30 messages → ≥ 90 % d'intention attendue.

- [ ] T030 [P] [US2] Écrire `backend/tests/orchestrator/test_intent_classifier.py` (RED) : règles, fallback LLM, cache TTL 600 s, fallback `autre` si LLM down, 30 cas test (FR-003, SC-001).
- [ ] T031 [US2] Implémenter `backend/app/orchestrator/intent_classifier.py` : `Intent` Literal, `RULES`, `classify(...)`, cache TTL maison ou `cachetools.TTLCache`, fallback LLM via `app.llm_client.get_llm_client()`. (GREEN T030).

## Phase 5 — User Story 3 : Tool selector (P1)

**Goal** : 5–10 tools max selon intention + page + skills ; defaults minimaux ; whitelist.
**Independent test** : 10 paires (intent, ctx) → set ≤ 10, jamais vide.

- [ ] T040 [P] [US3] Écrire `backend/tests/orchestrator/test_tool_selector.py` (RED) : règles, set par défaut `{ask_qcu, ask_yes_no}`, whitelist Skills (FR-017), limite hard 10.
- [ ] T041 [US3] Implémenter `backend/app/orchestrator/tool_selector.py` : règles déclaratives, `MAX_TOOLS=10`, defaults, intersection whitelist. (GREEN T040).

## Phase 6 — User Story 5 : System prompt builder (P1)

**Goal** : invariants + arbre décision + tools + contexte ; ≤ 4000 tokens ; alarme + troncature.
**Independent test** : prompt déterministe, plafond respecté.

- [ ] T050 [P] [US5] Écrire `backend/tests/orchestrator/test_system_prompt_builder.py` (RED) : briques présentes, déterminisme, troncature au-delà de 4000 tokens (estimation `len // 4`), pas de fuite cross-tenant.
- [ ] T051 [US5] Implémenter `backend/app/orchestrator/system_prompt_builder.py` : `INVARIANTS_TEXT`, `DECISION_TREE_TEXT`, `ANTI_EXAMPLES_TEXT` inline ; `build(tools, context, max_tokens=4000) -> str` ; troncature ordonnée (anti-exemples → exemples tools → descriptions). (GREEN T050).

## Phase 7 — User Story 6 : Payload validator (P1)

**Goal** : validation Pydantic stricte ; erreur structurée.
**Independent test** : 5 payloads malformés rejetés (SC-002).

- [ ] T060 [P] [US6] Écrire `backend/tests/orchestrator/test_payload_validator.py` (RED) : 5 cas malformés + tool inconnu lève `UnknownToolError`.
- [ ] T061 [US6] Implémenter `backend/app/orchestrator/payload_validator.py` : `validate(tool_name, payload)`, mapping Pydantic `ValidationError` → `ValidationErrorDetail`, helper `format_for_llm`. (GREEN T060).

## Phase 8 — User Story 7 : Retry policy (P1)

**Goal** : max 2 retries ; fallback texte ; tokens retry séparés.
**Independent test** : 2 invalides + 1 valide → exécuté ; toujours invalide → fallback (SC-003).

- [ ] T070 [P] [US7] Écrire `backend/tests/orchestrator/test_retry_policy.py` (RED) : 1 invalide puis 1 valide → `retries=1` ; 3 invalides → fallback ; prompt retry minimal.
- [ ] T071 [US7] Implémenter `backend/app/orchestrator/retry_policy.py` : `decide`, `build_retry_prompt`, `FALLBACK_TEXT`. (GREEN T070).

## Phase 9 — User Story 1 + Edge cases : Pipeline + thread lock (P1)

**Goal** : `respond()` end-to-end ; sérialisation par thread_id (FR-016).
**Independent test** : 10 cas E2E ; 2 requêtes concurrentes même thread → sérialisées (SC-001, SC-009).

- [ ] T080 [P] [US1] Écrire `backend/tests/orchestrator/test_thread_lock.py` (RED) : sérialisation même thread, parallélisme threads distincts, timeout 5 s.
- [ ] T081 [US1] Implémenter `backend/app/orchestrator/thread_lock.py` : `_LOCKS` dict + GC, `@asynccontextmanager thread_lock(...)`. (GREEN T080).
- [ ] T082 [US1] Écrire `backend/tests/orchestrator/test_pipeline_e2e.py` (RED) : 10 cas E2E, retry réussi, fallback, handler_error, timeout, isolation RLS.
- [ ] T083 [US1] Implémenter `backend/app/orchestrator/pipeline.py` : `async def respond(...) -> ChatResponse` orchestrant lock + classifier + selector + builder + LLM + validator + retry + log. (GREEN T082).

## Phase 10 — User Story 8 : Streaming SSE F14 events (P2)

**Goal** : 4+ events `thinking/tool_call_*` cohérents (SC-004).
**Independent test** : message → events dans l'ordre.

- [ ] T090 [P] [US8] Écrire `backend/tests/chat/test_chat_api_pipeline.py` (RED) : SSE contient ≥ 4 `thinking` + `tool_call_started` + `tool_call_completed` + `text_delta` + `message_done` ; F13 inchangé si `F14_PIPELINE_ENABLED=0`.
- [ ] T091 [US8] Modifier `backend/app/chat/llm_stream.py` : si `F14_PIPELINE_ENABLED=1`, déléguer à `app.orchestrator.pipeline.respond` ; sinon F13.
- [ ] T092 [US8] Modifier `backend/app/chat/api.py` : passer `sse_emit` callback au pipeline ; non-régression F13.

## Phase 11 — User Story 9 : Logging append-only + admin read (P2)

**Goal** : 100 % des appels journalisés ; isolation tenant (SC-005).
**Independent test** : 10 appels → 10 lignes ; lecture admin filtrée par account_id.

- [ ] T100 [P] [US9] Écrire `backend/tests/orchestrator/test_tool_call_log_persistence.py` (RED) : 10 appels en DB, RLS testée, no UPDATE/DELETE.
- [ ] T101 [US9] Implémenter `backend/app/orchestrator/log_repository.py` : `insert_log`, `list_by_thread`.
- [ ] T102 [P] [US9] Écrire `backend/tests/admin/test_admin_tool_call_logs_api.py` (RED) : GET 200 admin, 403 non-admin, filtres.
- [ ] T103 [US9] Implémenter `backend/app/admin/tool_call_logs.py` (router FastAPI).
- [ ] T104 [US9] Brancher le router dans `backend/app/main.py`.

## Phase 12 — Polish & validation finale

- [ ] T110 Lancer `cd backend && source .venv/bin/activate && pytest -q --cov=app --cov-report=term-missing tests/` ; corriger.
- [ ] T111 Vérifier `--cov=app/orchestrator/` ≥ 80 %.
- [ ] T112 Lancer `cd backend && source .venv/bin/activate && ruff check app/ tests/` ; corriger.
- [ ] T113 [P] Vérifier non-régression F01-F13 (`pytest tests/ -q`).
- [ ] T114 [P] Écrire `.cc-runtime/logs/manual-tests-14.md` (curl SSE, page admin, modes stub vs réel).
- [ ] T115 Vérifier non-régression contrat F13 (events `text_delta`/`message_done`/`error`).

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
