---
description: "Task list F53 — Agent LangGraph Core"
---

# Tasks: Agent LangGraph Core (orchestration backend câblée)

**Input**: Design documents from `/specs/053-agent-langgraph-core/`
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/sse-events.md, contracts/healthcheck-agent.openapi.yaml, quickstart.md
**Tests**: TDD obligatoire (constitution + global rules — 80 % min, 85 % cible sur `backend/app/agent/`). Tests E2E inclus, exécutables par l'agent `e2e-runner` Phase B'.

## Format: `[ID] [P?] [Story] Description`

- **[P]** : exécutable en parallèle (fichiers indépendants, pas de dépendance bloquante)
- **[Story]** : numéro d'user story (US1..US8) ou pas de label pour Setup/Foundational/Polish
- Tous les chemins sont des chemins absolus (ou relatifs au repo root)

## Path Conventions

- Backend Python : `backend/app/agent/...`, `backend/tests/...`, `backend/alembic/versions/...`
- Frontend Playwright E2E : `frontend/tests/e2e/...`
- Specs : `specs/053-agent-langgraph-core/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose** : initialiser les dépendances LangGraph, créer le squelette du module `app/agent/`, configurer mypy/coverage.

- [ ] T001 Ajouter les dépendances LangGraph dans `backend/pyproject.toml` (langgraph^0.2.74, langchain-core^0.3.21, langchain-openai^0.2.14, langgraph-checkpoint-postgres^2.0.10) puis `pip install -e .` dans `backend/.venv`
- [ ] T002 [P] Ajouter les variables `LLM_AGENT_*` dans `backend/.env.example` (LLM_AGENT_MODE=langgraph, LLM_AGENT_MAX_TOOLS=10, LLM_AGENT_MAX_RETRIES=2, LLM_AGENT_TIMEOUT_S=30.0, LLM_AGENT_TRACE=db)
- [ ] T003 [P] Créer le squelette du module `backend/app/agent/__init__.py` (exports vides initiaux : `compile_agent_graph`, `run_agent`)
- [ ] T004 [P] Créer le sous-dossier `backend/app/agent/nodes/__init__.py` (vide initialement)
- [ ] T005 [P] Créer ou mettre à jour `backend/alembic/README.md` documentant la coexistence Alembic / LangGraph `setup()` (cf. data-model section 5)
- [ ] T006 Vérifier que `mypy --strict backend/app/agent/` passe sur le squelette vide (configuration dans `pyproject.toml` à confirmer)

**Checkpoint** : module agent vide et importable, dépendances installées, env vars documentées.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose** : infrastructure transverse (settings, types, factories, migration, helpers) requise par TOUTES les user stories. Aucune US ne peut commencer avant la fin de cette phase.

**⚠️ CRITICAL** : aucune user story ne démarre avant que Phase 2 soit complète et verte.

### Configuration & types

- [ ] T007 Ajouter les champs `LLM_AGENT_*` dans `backend/app/config.py` (Pydantic `Settings`) avec types stricts (`Literal["langgraph", "raw"]`, `int`, `float`, `Literal["off", "db", "db+stdout"]`)
- [ ] T008 [P] Implémenter `backend/app/agent/state.py` : `AgentState` (Pydantic v2, `extra='forbid'`, reducers `add_messages`, `_append`), types `Intent` (StrEnum), `ContextJson`, `ToolCall`, `ValidatedToolCall`, `DispatchCategory`, `ToolDispatchResult`, `AgentError`
- [ ] T009 [P] [Test FIRST] Tests unitaires `backend/tests/unit/test_agent_state.py` : `extra='forbid'` rejette champs inconnus, regex thread_id valide/invalide, reducers fusionnent correctement, validation StrEnum (RED puis GREEN)

### Migration Alembic

- [ ] T010 Générer la migration Alembic `backend/alembic/versions/0XXX_agent_run_steps.py` (suivre exactement le contenu de data-model section 6 : tables agent_run + agent_run_step, ENUMs, indexes, RLS policies, REVOKE UPDATE/DELETE pour app_user)
- [ ] T011 Appliquer la migration en local : `cd backend && source .venv/bin/activate && alembic upgrade head` puis vérifier les tables et policies via `psql`
- [ ] T012 [Test FIRST] Test d'intégration `backend/tests/integration/test_agent_migration.py` : tables existent, RLS active, REVOKE appliqué, CHECK constraint thread_id format opérationnel (RED puis GREEN)

### Factories & helpers

- [ ] T013 [P] Implémenter `backend/app/agent/llm_factory.py` : `def build_chat_model(settings: Settings) -> ChatOpenAI` (utilise LLM_BASE_URL/LLM_API_KEY/LLM_MODEL ; pas de hard-code) ; pin streaming=True ; timeout=LLM_AGENT_TIMEOUT_S
- [ ] T014 [P] [Test FIRST] Tests unitaires `backend/tests/unit/test_agent_llm_factory.py` : monkeypatch des settings, vérifier que ChatOpenAI est instancié avec les bonnes params ; aucune call réseau (RED puis GREEN)
- [ ] T015 [P] Implémenter `backend/app/agent/tool_factory.py` : `def to_structured_tool(tool_def: ToolDef) -> StructuredTool` (description = `f"{use_when}\n\nDont use when: {dont_use_when}"`, args_schema = Pydantic schema du tool) ; helper `def list_active_tools(intent, max_tools) -> list[StructuredTool]` qui consume `app.orchestrator.tool_selector`
- [ ] T016 [P] [Test FIRST] Tests unitaires `backend/tests/unit/test_agent_tool_factory.py` : conversion ToolDef → StructuredTool, plafonnage max_tools, sélection par intent (RED puis GREEN)

### Concurrency & checkpointer

- [ ] T017 [P] Implémenter `backend/app/agent/concurrency.py` : helper `acquire_thread_lock(session, thread_id, timeout_s)` qui exécute `pg_advisory_xact_lock(hashtext(thread_id))` ou retourne 409 si timeout dépassé
- [ ] T018 [P] [Test FIRST] Test d'intégration `backend/tests/integration/test_agent_concurrency.py` : deux requêtes parallèles sur même thread_id ; la 2e attend ou retourne 409 (RED puis GREEN)
- [ ] T019 [P] Implémenter `backend/app/agent/checkpointer.py` : wrapper `AsyncPostgresSaver` avec validation du `thread_id` composite ; helper `validate_thread_id(thread_id, account_id)` qui vérifie le préfixe ; setup() au boot
- [ ] T020 [P] [Test FIRST] Tests unitaires `backend/tests/unit/test_agent_checkpointer.py` : validate_thread_id refuse mismatch préfixe, accepte format valide (RED puis GREEN)

### Tracing

- [ ] T021 [P] Implémenter `backend/app/agent/models.py` : SQLAlchemy ORM `AgentRun`, `AgentRunStep` (mappés sur les tables Alembic)
- [ ] T022 [P] Implémenter `backend/app/agent/repository.py` : `start_run`, `complete_run` (UPDATE app_admin role), `mark_run_cancelled`, `mark_run_timeout`, `record_step` ; toutes async ; respectent RLS via current_account_id
- [ ] T023 [P] Implémenter `backend/app/agent/tracing.py` : décorateur `@traced_node(node_name)` qui wrappe une fonction de nœud, mesure latence, écrit `agent_run_step` row ; helper `traced_run(...)` pour le runner
- [ ] T024 [P] [Test FIRST] Tests unitaires `backend/tests/unit/test_agent_tracing.py` : mock repository, vérifier que les rows sont écrits avec les bonnes valeurs ; vérifier reentrancy safe (RED puis GREEN)

**Checkpoint** : settings, types, migration, factories, concurrency, checkpointer, tracing sont tous prêts et testés. La user story 1 peut démarrer.

---

## Phase 3: User Story 1 - Création de projet via tool calls validés (Priority: P1) 🎯 MVP

**Goal** : une PME peut créer un projet via le chat. L'agent identifie l'intention de mutation, déclenche bottom sheet, valide les réponses, écrit en DB avec audit log, push EventBus front.

**Independent Test** : pytest E2E (`backend/tests/e2e/test_agent_e2e_create_project.py`) + Playwright (`frontend/tests/e2e/agent-chat-create-project.spec.ts`) — tous deux valident le scénario complet sans réécriture du code en US suivantes.

### Tests for User Story 1 (TDD obligatoire) ⚠️

> **NOTE: Écrire ces tests EN PREMIER, vérifier qu'ils échouent (RED), puis implémenter pour passer (GREEN).**

- [ ] T025 [P] [US1] Test E2E backend `backend/tests/e2e/test_agent_e2e_create_project.py` : POST /messages avec « Crée un projet de panneaux solaires de 50 kWc » → fakellm retourne tool call `ask_qcu` puis `create_projet` → vérifier SSE events (`tool_invoke`, `mutation`), DB row projet créé, audit_log row avec `source_of_change=llm`, EventBus poussé (mock event collector)
- [ ] T026 [P] [US1] Test Playwright `frontend/tests/e2e/agent-chat-create-project.spec.ts` : login PME → page chat → envoyer message → bottom sheet apparaît → valider montant/lieu/date → projet visible dans Profil → Projets sans rechargement (utiliser `page.waitForResponse` pour SSE et `page.expect.toBeVisible` pour le projet créé)
- [ ] T027 [P] [US1] Test d'intégration `backend/tests/integration/test_agent_graph.py::test_route_to_dispatch_create` : flow complet route → context → memory → select_tools → call_llm → validate → dispatch (mocker fakellm) ; vérifier les rows agent_run + agent_run_step
- [ ] T028 [P] [US1] Test unitaire `backend/tests/unit/test_agent_nodes_dispatch.py::test_dispatch_create_projet` : nœud dispatch_tool reçoit ValidatedToolCall create_projet, appelle handler F17, écrit audit, retourne ToolDispatchResult avec `db_audit_id`

### Implementation for User Story 1

#### Nœuds essentiels

- [ ] T029 [US1] Implémenter `backend/app/agent/nodes/route.py` : `async def node_route(state: AgentState) -> dict` qui appelle `app.orchestrator.intent_classifier.classify(state.user_message, state.context_json)` et écrit `intent` ; décoré `@traced_node("route")`
- [ ] T030 [US1] Implémenter `backend/app/agent/nodes/build_context.py` : version minimale F53 qui injecte `user_message` + `context_json` + ID PME dans `messages` HumanMessage ; F54 polishera ensuite. Branchement intent → ctx_full vs ctx_min
- [ ] T031 [US1] Implémenter `backend/app/agent/nodes/recall_memory.py` : appelle `app.chat.memory.recall(thread_id, account_id, k=15)` et ajoute les messages au state ; respecte RLS
- [ ] T032 [US1] Implémenter `backend/app/agent/nodes/select_tools.py` : appelle `app.orchestrator.tool_selector.select(intent, context, max=settings.LLM_AGENT_MAX_TOOLS)` ; convertit en `available_tools` via `tool_factory`
- [ ] T033 [US1] Implémenter `backend/app/agent/nodes/call_llm.py` : invoque `chat_model.bind_tools(state.available_tools).astream(messages)` ; émet events SSE (`token`, `tool_invoke` partiels) ; collecte `tool_calls` et `llm_response` final
- [ ] T034 [US1] Implémenter `backend/app/agent/nodes/validate_payload.py` : pour chaque tool call, exécute `app.orchestrator.payload_validator.validate(tool_name, args)` ; retourne ValidatedToolCall ou retry signal ; gère `retry_count` ; écrit `tool_call_log` row
- [ ] T035 [US1] Implémenter `backend/app/agent/nodes/dispatch_tool.py` : routage 3 voies (SSE_ONLY, DB_MUTATION, REINVOKE_LLM) ; pour DB_MUTATION : appelle handler F17 sous RLS via `set_account_context(account_id, user_id)` ; écrit audit log ; émet SSE `mutation` ; retourne ToolDispatchResult
- [ ] T036 [US1] Implémenter `backend/app/agent/nodes/compose_response.py` : assemble `final_text` à partir des résultats, persiste le message assistant via `app.chat.service.persist_assistant_turn(...)` (sauf si run cancelled ou timeout)

#### Graph et runner

- [ ] T037 [US1] Implémenter `backend/app/agent/graph.py` : `def build_graph() -> StateGraph[AgentState]` qui assemble les 8 nœuds, définit les transitions conditionnelles (route → build_context, validate_payload → dispatch_tool si OK, validate_payload → call_llm si retry, dispatch_tool → call_llm si REINVOKE_LLM tools, dispatch_tool → compose_response sinon)
- [ ] T038 [US1] Implémenter `backend/app/agent/sse_bridge.py` : helpers de mapping `langgraph_event → sse_event` (tokens, tool_invoke, mutation, validation_retry, error, done) ; aligné avec `contracts/sse-events.md`
- [ ] T039 [US1] Implémenter `backend/app/agent/runner.py` : `async def run_agent(...) -> AsyncIterator[SseEvent]` qui : (a) acquiert advisory lock, (b) start_run, (c) `graph.astream_events(version='v2')`, (d) map vers SSE, (e) try/except CancelledError → mark_run_cancelled, (f) complete_run sur succès ; valide thread_id composite vs account_id
- [ ] T040 [US1] Implémenter `backend/app/agent/__init__.py` : exports `compile_agent_graph`, `run_agent` ; le `compile_agent_graph()` instancie le checkpointer (.setup() async), build le graph, le compile une fois

#### Branchement chat/api.py

- [ ] T041 [US1] Modifier `backend/app/chat/api.py:post_message` pour brancher : if `settings.LLM_AGENT_MODE == "langgraph"` → `run_agent(...)` ; else → `stream_assistant(...)` (préservé). Wrapper dans `StreamingResponse(media_type="text/event-stream")`
- [ ] T042 [US1] Modifier `backend/app/main.py` : lifespan FastAPI ajoute `app.state.agent_graph = await compile_agent_graph()` au startup si `LLM_AGENT_MODE == "langgraph"` ; logguer durée de boot

**Checkpoint US1** : SC-001 vert. Une PME peut créer un projet via le chat. Tests E2E + Playwright passent. Audit log écrit. EventBus front poussé. Coverage agent ≥ 70 % (cible finale 85 % atteinte au Polish).

---

## Phase 4: User Story 2 - Analyse ESG avec mémoire et sourçage (Priority: P1)

**Goal** : l'agent répond à une question d'analyse en chargeant la mémoire, exécutant `recall_history`, retournant un radar viz et un texte sourcé via `cite_source`.

**Independent Test** : pytest E2E `backend/tests/e2e/test_agent_e2e_analysis_sourced.py` valide la chaîne `recall_history → show_radar_chart → texte + cite_source(BOAD-2024)` avec fakellm scénarisé.

### Tests for User Story 2 ⚠️

- [ ] T043 [P] [US2] Test E2E backend `backend/tests/e2e/test_agent_e2e_analysis_sourced.py` : POST /messages « Quel score ESG attendu pour ma boulangerie ? » → fakellm retourne `recall_history` puis `show_radar_chart` puis `cite_source(source_id=BOAD-2024)` puis texte final → vérifier SSE events (`tool_invoke` radar, `done` avec final_text), absence de chiffre non sourcé
- [ ] T044 [P] [US2] Test d'intégration `backend/tests/integration/test_agent_graph.py::test_recall_then_viz_then_source` : flow REINVOKE_LLM (recall_history retourne data, re-call LLM produit suite) ; vérifier la boucle se termine correctement
- [ ] T045 [P] [US2] Test unitaire `backend/tests/unit/test_agent_nodes_dispatch.py::test_dispatch_reinvoke_llm` : tool category REINVOKE_LLM (cite_source, recall_history) → résultat injecté en message tool puis flow rebascule sur call_llm

### Implementation for User Story 2

- [ ] T046 [US2] Étendre `backend/app/agent/nodes/dispatch_tool.py` pour la voie REINVOKE_LLM : exécuter le tool (recall_history, cite_source, search_source), construire un message `ToolMessage` avec le résultat, l'ajouter à `state.messages`, et signaler au graph de re-router vers `call_llm` (via state flag ou conditional edge)
- [ ] T047 [US2] Étendre `backend/app/agent/graph.py` avec edge conditionnel `dispatch_tool → call_llm` quand `dispatch_results.contains(REINVOKE_LLM)` ET `retry_count < MAX_RETRIES` ; sinon → compose_response
- [ ] T048 [US2] Garde-fou anti-boucle infinie : compteur `reinvoke_count` distinct de `retry_count`, plafonné à 3 par tour ; au-delà, fallback texte + log warning

**Checkpoint US2** : SC-002 vert. Le test golden set 50 messages sourcés est prêt à être exécuté en F58 (data + tooling déjà accessibles).

---

## Phase 5: User Story 3 - Boucle Validate ↔ Retry sur hallucination (Priority: P1)

**Goal** : un tool call invalide est rejeté → erreur Pydantic structurée renvoyée au LLM → retry → succès. Au-delà de 2 retries → fallback texte sobre.

**Independent Test** : pytest unit + integration `backend/tests/integration/test_agent_graph.py::test_validate_retry_loop` avec fakellm scénarisé (1 tool call invalide puis 1 valide → succès, ou 2 invalides → fallback).

### Tests for User Story 3 ⚠️

- [ ] T049 [P] [US3] Test d'intégration `backend/tests/integration/test_agent_graph.py::test_validate_retry_succeeds_on_2nd_attempt` : fakellm retourne payload invalide (champ extra), agent renvoie erreur structurée, fakellm retourne payload valide, dispatch s'exécute, `retry_count=1` dans agent_run, message final correct
- [ ] T050 [P] [US3] Test d'intégration `backend/tests/integration/test_agent_graph.py::test_validate_retry_fallback_after_max` : 2 hallucinations consécutives → fallback texte sobre, `agent_run.status='error'`, `tool_call_log.status='validation_error'`
- [ ] T051 [P] [US3] Test unitaire `backend/tests/unit/test_agent_nodes_validate.py` : retry_count incrément, format de l'erreur structurée renvoyée au LLM (ToolMessage avec content JSON), respect de LLM_AGENT_MAX_RETRIES

### Implementation for User Story 3

- [ ] T052 [US3] Étendre `backend/app/agent/nodes/validate_payload.py` : sur erreur Pydantic, formater une `ToolMessage(tool_call_id=..., content=json.dumps({"error": "...", "details": {...}}))` et l'ajouter à state.messages ; incrémenter retry_count ; signaler edge conditionnel vers call_llm
- [ ] T053 [US3] Étendre `backend/app/agent/graph.py` avec edge conditionnel `validate_payload → call_llm` si retry_count < MAX, sinon → compose_response (chemin fallback)
- [ ] T054 [US3] Implémenter le message fallback dans `compose_response.py` : si state.errors contient `validation_error` non récupéré, retourner texte sobre FR « Je n'arrive pas à formaliser cette action — peux-tu reformuler ? » ; ne PAS persister tool calls

**Checkpoint US3** : SC-003 + SC-004 verts. Robustesse anti-hallucination garantie.

---

## Phase 6: User Story 4 - Isolation multi-tenant stricte de l'agent (Priority: P1)

**Goal** : aucun agent A ne peut voir/toucher une entité du compte B, même avec UUID exact. Cross-tenant → 404, jamais 403, jamais leak.

**Independent Test** : pytest `backend/tests/integration/test_agent_cross_tenant.py` lance 50 tentatives variées de leak.

### Tests for User Story 4 ⚠️

- [ ] T055 [P] [US4] Test d'intégration `backend/tests/integration/test_agent_cross_tenant.py::test_dispatch_cross_tenant_returns_404` : compte A authentifié envoie « supprime projet UUID-de-B » → fakellm produit `delete_projet(id=UUID-B)` → dispatch RLS empêche la lecture → ToolDispatchResult.status='error' code='not_found' ; aucune ligne audit côté B ; agent répond comme si l'entité n'existait pas
- [ ] T056 [P] [US4] Test d'intégration `backend/tests/integration/test_agent_cross_tenant.py::test_thread_id_prefix_mismatch` : thread_id avec préfixe account différent de la session → 404 avant même d'invoquer le checkpointer (validation runner)
- [ ] T057 [P] [US4] Test d'intégration `backend/tests/integration/test_agent_cross_tenant.py::test_50_cross_tenant_attempts` : matrice de 50 tentatives variées (UUID corrects, références indirectes par nom) → 100 % retournent neutralement, aucune fuite SQL dans les logs ; valide SC-005

### Implementation for User Story 4

- [ ] T058 [US4] Étendre `backend/app/agent/runner.py` : valider `thread_id` composite contre `account_id` AVANT toute action (advisory lock, checkpointer, graph) ; lever `HTTPException(404)` sur mismatch ; ne pas log d'indice
- [ ] T059 [US4] Étendre `backend/app/agent/nodes/dispatch_tool.py` : tous les handlers DB_MUTATION DOIVENT être appelés sous `with set_account_context(account_id, user_id):` (déjà l'API existante F02) ; capturer les `NoResultFound` et les transformer en `ToolDispatchResult(status='error', error_summary='not_found')`
- [ ] T060 [US4] Sanitize les error_summary pour ne JAMAIS leak de UUID d'autres comptes ni de données sensibles dans les SSE events ou les logs (linter custom ou helper `safe_error_message`)

**Checkpoint US4** : SC-005 vert. Isolation tenant garantie au niveau agent.

---

## Phase 7: User Story 5 - Branchement effectif et rollback opérationnel (Priority: P1)

**Goal** : bascule instantanée entre `LLM_AGENT_MODE=langgraph` et `raw` via env var, sans rebuild ni migration. Les 2 modes restent fonctionnels.

**Independent Test** : pytest `backend/tests/integration/test_agent_modes.py` exécute les deux modes en CI parallèle (matrice).

### Tests for User Story 5 ⚠️

- [ ] T061 [P] [US5] Test d'intégration `backend/tests/integration/test_agent_modes.py::test_langgraph_mode` : LLM_AGENT_MODE=langgraph, POST /messages → run_agent appelé, agent_run row créé, SSE conforme protocole F53
- [ ] T062 [P] [US5] Test d'intégration `backend/tests/integration/test_agent_modes.py::test_raw_mode` : LLM_AGENT_MODE=raw, POST /messages → stream_assistant appelé, AUCUN agent_run row créé, SSE classique sans tool_invoke/mutation
- [ ] T063 [P] [US5] Test d'intégration `backend/tests/integration/test_agent_health.py::test_health_agent_endpoint` : `GET /health/agent` retourne payload conforme `contracts/healthcheck-agent.openapi.yaml` ; mode=langgraph et raw

### Implementation for User Story 5

- [ ] T064 [US5] Implémenter `backend/app/agent/api.py` : router `/health/agent` (GET) qui vérifie `langgraph_compiled`, `postgres_checkpointer`, `llm_reachable` (HEAD ping LLM_BASE_URL), retourne 200/503 selon spec OpenAPI
- [ ] T065 [US5] Modifier `backend/app/main.py` : registrer le router agent (`app.include_router(agent_api.router, prefix="/health")`) ; en mode raw, le compile est skip mais l'endpoint reste informatif
- [ ] T066 [US5] Documenter dans `backend/.env.example` un commentaire clair : `LLM_AGENT_MODE=raw` désactive l'agent et restaure le proxy LLM brut, sans rebuild ; ne nécessite que reload de l'env

**Checkpoint US5** : SC-008 vert. Rollback opérationnel zéro-downtime.

---

## Phase 8: User Story 6 - Persistance et reprise après crash (Priority: P2)

**Goal** : checkpoints LangGraph persistés en Postgres permettent de reprendre une conversation après redémarrage.

**Independent Test** : pytest `backend/tests/integration/test_agent_checkpoint.py` simule restart et vérifie restauration.

### Tests for User Story 6 ⚠️

- [ ] T067 [P] [US6] Test d'intégration `backend/tests/integration/test_agent_checkpoint.py::test_resume_after_restart` : démarrer un thread, snapshotter état, simuler restart (re-instancier checkpointer) → état restauré identique
- [ ] T068 [P] [US6] Test d'intégration `backend/tests/integration/test_agent_checkpoint.py::test_concurrent_writes_same_thread` : déjà couvert par advisory lock T018 mais valider conjointement avec checkpoints

### Implementation for User Story 6

- [ ] T069 [US6] Compléter `backend/app/agent/checkpointer.py` avec `compile_agent_graph()` qui call `await checkpointer.setup()` au boot (idempotent) ; intégrer dans `__init__.py:compile_agent_graph()`
- [ ] T070 [US6] Vérifier que les tables `checkpoints*` sont bien créées au boot via test d'intégration
- [ ] T071 [US6] Documenter dans `backend/alembic/README.md` (étendu T005) la liste exacte des tables LangGraph et l'interdiction de les versionner Alembic

**Checkpoint US6** : SC-010 vert.

---

## Phase 9: User Story 7 - Tracing et observabilité (Priority: P2)

**Goal** : chaque tour produit `agent_run` row + N `agent_run_step` rows. Requête SQL par thread_id reconstitue la timeline.

**Independent Test** : pytest `backend/tests/integration/test_agent_tracing.py`.

### Tests for User Story 7 ⚠️

- [ ] T072 [P] [US7] Test d'intégration `backend/tests/integration/test_agent_tracing.py::test_run_writes_run_and_steps` : 1 message → 1 agent_run row + ≥7 agent_run_step rows, latence > 0, tokens > 0
- [ ] T073 [P] [US7] Test d'intégration `backend/tests/integration/test_agent_tracing.py::test_run_status_timeout` : LLM_AGENT_TIMEOUT_S=0.1 sur fakellm slow → agent_run.status='timeout', step concerné taggé timeout
- [ ] T074 [P] [US7] Test d'intégration `backend/tests/integration/test_agent_tracing.py::test_append_only_enforced` : tenter UPDATE/DELETE sur agent_run en tant que app_user → rejeté ; idem agent_run_step

### Implementation for User Story 7

- [ ] T075 [US7] Compléter `backend/app/agent/tracing.py` : décorateur `@traced_node` correctement intégré dans tous les nœuds T029-T036 ; mesure `time.perf_counter()` ; tokens via metadata LangChain
- [ ] T076 [US7] Implémenter le mode trace `db+stdout` (LLM_AGENT_TRACE option) : structured JSON log par event en plus des rows DB
- [ ] T077 [US7] Vérifier append-only : si `LLM_AGENT_TRACE=off`, pas d'écriture DB ; si `db` ou `db+stdout`, écriture systématique

**Checkpoint US7** : SC-009 + observabilité ops opérationnelle.

---

## Phase 10: User Story 8 - Annulation côté client (Priority: P1)

**Goal** : sur déconnexion SSE client, propager `asyncio.CancelledError`, marquer `agent_run.status='cancelled'`, ne persister aucun message tronqué, libérer les ressources.

**Independent Test** : pytest `backend/tests/integration/test_agent_cancellation.py` simule disconnect SSE après 1s sur run de 10s.

### Tests for User Story 8 ⚠️

- [ ] T078 [P] [US8] Test d'intégration `backend/tests/integration/test_agent_cancellation.py::test_sse_disconnect_marks_cancelled` : démarrer SSE, déconnecter après 1s pendant un nœud LLM lent (fakellm sleep) → agent_run.status='cancelled', aucun message assistant complet en DB
- [ ] T079 [P] [US8] Test d'intégration `backend/tests/integration/test_agent_cancellation.py::test_cancellation_during_db_mutation` : disconnect pendant dispatch_tool DB_MUTATION → transaction rollback, aucune ligne audit, status='cancelled'
- [ ] T080 [P] [US8] Test Playwright `frontend/tests/e2e/agent-chat-cancellation.spec.ts` : envoyer message → cliquer bouton Stop dans la bulle assistant après 1s → SSE se ferme proprement, message bulle non finalisée, pas d'erreur visuelle

### Implementation for User Story 8

- [ ] T081 [US8] Implémenter le bouton « Stop » dans la bulle assistant côté frontend (F41) : sur click, `eventSource.close()` + indicateur visuel « Annulé » ; déjà ébauché en F41 (à finaliser)
- [ ] T082 [US8] Compléter `backend/app/agent/runner.py` avec try/except `asyncio.CancelledError` correctement pipé : `mark_run_cancelled` puis `raise` (cf. research D8)
- [ ] T083 [US8] Vérifier que `compose_response.py` ne persiste PAS de message si la run est cancelled (check status avant `persist_assistant_turn`)

**Checkpoint US8** : SC-007 vert.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose** : qualité finale, doc, perf, sec.

- [ ] T084 [P] Nettoyer le code : extraire les helpers communs (set_account_context wrapper, error sanitizer) ; vérifier que chaque fichier `app/agent/*.py` < 400 lignes ; refactor si dépassement
- [ ] T085 [P] Vérifier `mypy --strict backend/app/agent/` passe sans `# type: ignore` (NFR-004)
- [ ] T086 [P] Vérifier `ruff check backend/app/agent/` passe (config `select = E,F,W,I,B,UP`, line-length=100)
- [ ] T087 Vérifier coverage : `pytest tests/ -k "agent" --cov=app/agent --cov-fail-under=85` (NFR-005, SC-009)
- [ ] T088 [P] Test de perf NFR-001 : benchmark pipeline (route + context + select + validate + dispatch hors LLM) sur 100 itérations ; assert p95 < 500ms ; ajouter dans `backend/tests/perf/test_agent_perf.py` (marker pytest `perf`)
- [ ] T089 [P] Test de perf NFR-003 : mémoire RAM par exécution mesurée via `tracemalloc` ; assert peak < 50 MB
- [ ] T090 [P] Test de boot NFR/SC-004 : mesurer durée de `compile_agent_graph()` ; assert < 5s en local
- [ ] T091 [P] Mettre à jour `backend/.env.example` final avec commentaires explicatifs sur chaque LLM_AGENT_*
- [ ] T092 [P] Documenter dans `backend/alembic/README.md` (final) les tables LangGraph gérées hors-Alembic + l'isolation par thread_id composite
- [ ] T093 Audit security : vérifier qu'aucun secret n'est loggé, que les error_summary ne leak pas (test grep automatique sur les logs E2E)
- [ ] T094 Exécuter `quickstart.md` étape par étape (rejoue par l'agent E2E runner Phase B') ; tous les checkpoints doivent passer
- [ ] T095 [P] Mettre à jour `CLAUDE.md` (déjà fait au plan T+0) — vérifier que le pointeur SPECKIT pointe bien vers `specs/053-agent-langgraph-core/plan.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** : T001-T006, exécutables en parallèle dans la mesure du possible. T001 (pyproject) bloque les autres car il installe les libs.
- **Foundational (Phase 2)** : T007-T024, peut commencer après T001. T010-T012 (migration) peut tourner en parallèle de T013-T024 (factories/types) en partie.
- **User Story 1 (Phase 3)** : démarre après Phase 2 complète. C'est l'épine dorsale (graph + nodes + runner + branchement). Aucune autre US ne peut démarrer avant T029-T042 (les nœuds + graph + runner) car elles enrichissent ces fichiers.
- **User Story 2-8 (Phases 4-10)** : démarrent après Phase 3. Peuvent partiellement se chevaucher entre elles (US4-US5-US6-US7-US8 touchent des fichiers ou aspects différents — voir parallélisation ci-dessous).
- **Polish (Phase 11)** : démarre après toutes les US.

### User Story Dependencies

- **US1 (P1)** : aucune dépendance autre que Phase 2.
- **US2 (P1)** : dépend de US1 (étend dispatch_tool et graph).
- **US3 (P1)** : dépend de US1 (étend validate_payload et graph).
- **US4 (P1)** : dépend de US1 (étend runner et dispatch_tool ; ajoute tests cross-tenant).
- **US5 (P1)** : dépend de US1 (modif chat/api.py et main.py — déjà touchés en US1, mais US5 finit le branchement complet).
- **US6 (P2)** : dépend de US1 (utilise checkpointer déjà construit en Phase 2 ; complète l'integration).
- **US7 (P2)** : dépend de US1 (le tracing est appliqué aux nœuds livrés en US1).
- **US8 (P1)** : dépend de US1 (modif runner et compose_response).

### Within Each User Story

- Tests FIRST (RED) → Implémentation (GREEN) → Refactor.
- Modèles avant services, services avant endpoints, core avant intégration.
- Story complète avant de passer à la suivante (sauf parallélisation explicite ci-dessous).

### Parallel Opportunities

#### Au sein de Phase 2 (Foundational)

Après T001 :
- T002, T003, T004, T005 [P] (env/structures)
- T008-T009 [P] (state.py + tests)
- T010-T012 [P] (migration + tests, séparé)
- T013-T014 [P] (llm_factory + tests)
- T015-T016 [P] (tool_factory + tests)
- T017-T018 [P] (concurrency + tests)
- T019-T020 [P] (checkpointer + tests)
- T021-T022-T023-T024 [P] (tracing models/repo/decorator + tests)

Soit 6-8 tâches simultanées possibles.

#### Au sein de US1

T025-T028 [P] (4 tests RED en parallèle).
T029-T036 [P] partiellement (chaque nœud est dans son fichier, mais tous dépendent de state.py et factories).

#### Entre US (après US1)

US3 (T049-T054) // US6 (T067-T071) // US7 (T072-T077) // US4 (T055-T060) en partie peuvent avancer en parallèle car ils touchent des fichiers différents :
- US3 → validate_payload.py + graph.py (edge)
- US4 → runner.py + dispatch_tool.py (security)
- US6 → checkpointer.py + alembic/README.md
- US7 → tracing.py + nodes (decorator integration)

US2, US5, US8 dépendent plus directement du graph+runner et doivent être séquencées prudemment.

---

## Parallel Example: Foundational + User Story 1

```bash
# Phase 2 — Foundational (after T001)
Task: "T002 + T003 + T004 + T005 (env/skeleton)"
Task: "T008 + T009 (state + tests RED then GREEN)"
Task: "T010-T012 (migration + tests)"
Task: "T013-T024 (factories, helpers, tracing) — 6 fichiers parallèles"

# Phase 3 — User Story 1 (after Phase 2)
Task: "T025 (E2E backend test RED)"
Task: "T026 (Playwright test RED)"
Task: "T027 (integration test RED)"
Task: "T028 (unit test RED)"

# Then implementation in sequence (graph nodes need state, factories ready)
Task: "T029 + T030 + T031 + T032 (4 nodes simple/independent)"
Task: "T033 + T034 + T035 (3 nodes with deps on previous)"
Task: "T036 + T037 + T038 + T039 + T040 (graph wiring + runner)"
Task: "T041 + T042 (branchement chat/api.py + main.py)"
```

---

## E2E test files (planifiés)

**Backend pytest E2E** (httpx + ASGI, mock LLM via fakellm) :
- `backend/tests/e2e/test_agent_e2e_create_project.py` (T025, US1, SC-001)
- `backend/tests/e2e/test_agent_e2e_analysis_sourced.py` (T043, US2, SC-002)

**Backend pytest integration** (RLS-aware, real DB, mock LLM) :
- `backend/tests/integration/test_agent_graph.py` (T027, T044, T049-T050)
- `backend/tests/integration/test_agent_cross_tenant.py` (T055-T057, US4, SC-005)
- `backend/tests/integration/test_agent_cancellation.py` (T078-T079, US8, SC-007)
- `backend/tests/integration/test_agent_checkpoint.py` (T067-T068, US6, SC-010)
- `backend/tests/integration/test_agent_concurrency.py` (T018, advisory lock)
- `backend/tests/integration/test_agent_health.py` (T063, US5, FR-015)
- `backend/tests/integration/test_agent_modes.py` (T061-T062, US5, SC-008)
- `backend/tests/integration/test_agent_tracing.py` (T072-T074, US7, FR-011)
- `backend/tests/integration/test_agent_migration.py` (T012, append-only enforcement)

**Backend pytest perf** (markers `perf`) :
- `backend/tests/perf/test_agent_perf.py` (T088-T090, NFR-001/003/004)

**Backend pytest unit** :
- `backend/tests/unit/test_agent_state.py` (T009)
- `backend/tests/unit/test_agent_llm_factory.py` (T014)
- `backend/tests/unit/test_agent_tool_factory.py` (T016)
- `backend/tests/unit/test_agent_checkpointer.py` (T020)
- `backend/tests/unit/test_agent_tracing.py` (T024)
- `backend/tests/unit/test_agent_nodes_route.py` (intégré T029)
- `backend/tests/unit/test_agent_nodes_validate.py` (T051)
- `backend/tests/unit/test_agent_nodes_dispatch.py` (T028, T045)
- `backend/tests/unit/test_agent_nodes_compose.py`

**Frontend Playwright E2E** :
- `frontend/tests/e2e/agent-chat-create-project.spec.ts` (T026, US1, SC-001 chaîne UI complète)
- `frontend/tests/e2e/agent-chat-cancellation.spec.ts` (T080, US8, SC-007 bouton Stop)

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 : Setup
2. Phase 2 : Foundational (CRITIQUE — bloque tout)
3. Phase 3 : US1 (création projet via tool calls)
4. **STOP & VALIDATE** : SC-001 vert, démo possible
5. Coverage à ce stade : ~70 %, focus sur le path principal

### Incremental Delivery

1. Setup + Foundational → infra prête
2. + US1 → MVP démontrable (SC-001) — DEPLOY
3. + US2 (analyse sourcée) → SC-002
4. + US3 (retry) → SC-003 + SC-004 (robustesse)
5. + US4 (cross-tenant) → SC-005 (security)
6. + US5 (rollback) → SC-008 (ops)
7. + US8 (cancellation) → SC-007 (UX critique)
8. + US6 (checkpoint resume) → SC-010 (P2)
9. + US7 (tracing) → SC-009 (P2 ops)
10. + Polish → coverage ≥85 %, perf, doc

### Parallel Team Strategy

Avec 2-3 devs après Phase 2 :
- Dev A : US1 (épine dorsale)
- Dev B : US4 (cross-tenant tests, peut commencer dès que dispatch_tool stub est posé)
- Dev C : US7 (tracing, peut commencer dès que models.py + repository.py sont là)

US2/US3/US5/US6/US8 séquentielles après US1 (Dev A).

---

## Notes

- [P] tasks = fichiers différents, pas de dépendances bloquantes
- [Story] label = traçabilité user story → tâche
- Chaque user story est indépendamment testable (sauf US2-US8 qui dépendent de US1 pour l'épine dorsale)
- TDD obligatoire : tests RED puis GREEN puis refactor
- Commit après chaque tâche ou groupe logique (l'orchestrateur gère les commits en série)
- Stop à chaque checkpoint pour valider isolément
- Éviter : tâches vagues, conflits sur même fichier, dépendances cross-story qui cassent l'indépendance

## Total Task Count

- Phase 1 (Setup) : 6 tasks
- Phase 2 (Foundational) : 18 tasks (T007-T024)
- Phase 3 (US1) : 18 tasks (T025-T042)
- Phase 4 (US2) : 6 tasks (T043-T048)
- Phase 5 (US3) : 6 tasks (T049-T054)
- Phase 6 (US4) : 6 tasks (T055-T060)
- Phase 7 (US5) : 6 tasks (T061-T066)
- Phase 8 (US6) : 5 tasks (T067-T071)
- Phase 9 (US7) : 6 tasks (T072-T077)
- Phase 10 (US8) : 6 tasks (T078-T083)
- Phase 11 (Polish) : 12 tasks (T084-T095)

**Total : 95 tasks**, ~25 marquées [P] (parallélisables), 8 user stories couvrant 18 FR + 7 NFR + 10 SC.

## Format validation

- ✅ Toutes les tasks ont un checkbox `- [ ]`
- ✅ Toutes les tasks ont un ID séquentiel (T001 → T095)
- ✅ Tasks Phase 3-10 portent un label [USx]
- ✅ Tasks Phase 1, 2, 11 N'ont PAS de label US (per template)
- ✅ Tasks parallélisables marquées [P]
- ✅ Chaque task référence un chemin de fichier précis
