---

description: "Task list for F55 — Agent Tool Dispatch & SSE Bridge"
---

# Tasks: Agent Tool Dispatch & SSE Bridge

**Input**: Design documents from `/specs/055-agent-tool-dispatch-sse/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (sse-events.md + dispatcher-api.md), quickstart.md

**Tests**: TDD imposé par la constitution (`testing.md` ≥ 80 % global, ≥ 90 % sur dispatcher/mutation_ctx/rate_limit). Tests E2E exécutables (Playwright .spec.ts + pytest E2E backend) sont OBLIGATOIRES (cf. brief orchestrateur).

**Organization** : tasks groupées par user story pour permettre implémentation/testing indépendants.

## Format: `[ID] [P?] [Story] Description`

- **[P]** : peut tourner en parallèle (fichiers différents, pas de dépendance non terminée).
- **[Story]** : US1..US7 mappés sur user stories de spec.md.
- Chemins absolus dans les descriptions.

## Path Conventions

- Web app : `backend/app/`, `backend/tests/`, `frontend/app/`, `frontend/tests/`.
- Migrations : `backend/alembic/versions/`.
- Specs Playwright : `frontend/tests/e2e/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose** : préparer la branche, installer dépendances, vérifier que F53 est accessible.

- [ ] T001 Vérifier que la branche `055-agent-tool-dispatch-sse` est checkout et `main` à jour (`git fetch && git status` vert sauf `.cc-runtime/logs/orchestration.log`).
- [ ] T002 [P] Vérifier que `backend/.venv` est actif avec `pip list | grep -E '(langchain|langgraph|fastapi|sqlalchemy|pydantic|alembic|httpx)'` ; si manquant, `make setup` puis `pip install -e ./backend[dev]`.
- [ ] T003 [P] Vérifier que `frontend/node_modules` est installé (`pnpm install` au besoin).
- [ ] T004 [P] Vérifier que Postgres est up (`make db-up && docker compose ps`) et que la DB est à `head` (`make migrate`).
- [ ] T005 [P] Ajouter les nouvelles env vars dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/.env.example` (en mode ajout, jamais modif des lignes existantes) : `LLM_AGENT_RATE_LIMIT_BACKEND=memory`, `LLM_AGENT_RATE_LIMITS={"update_*":30,"create_*":10,"delete_*":5,"generate_*":5}`, `LLM_AGENT_READ_BUDGET_TOKENS=1500`, `LLM_AGENT_DRY_RUN_HEADER=X-Agent-DryRun`, `LLM_AGENT_CONFIRMATION_TTL_SECONDS=180`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose** : socle sans lequel aucune US ne peut démarrer (migration DB, types Pydantic, registry de catégories, fail-fast au boot).

⚠️ CRITICAL : aucune US n'avance avant la fin de cette phase.

### Migration Alembic

- [ ] T010 Créer la migration Alembic `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/alembic/versions/XXXX_f55_audit_tool_call_extensions.py` (revision auto-généré via `alembic revision --autogenerate -m "f55 audit tool call extensions"` puis ajustement manuel) qui ajoute :
  - `audit_log.tool_call_id UUID NULL FK tool_call_log(id)` + INDEX `idx_audit_log_tool_call_id`.
  - `audit_log.agent_run_id UUID NULL FK agent_run(id)`.
  - `tool_call_log.idempotency_key TEXT NULL`.
  - `tool_call_log.agent_run_id UUID NULL FK agent_run(id)`.
  - `tool_call_log.dispatch_result_kind TEXT NULL` (CHECK IN frontend_event|mutation_result|tool_message|error).
  - `CREATE UNIQUE INDEX idx_tool_call_log_account_idempotency ON tool_call_log(account_id, idempotency_key) WHERE idempotency_key IS NOT NULL`.
- [ ] T011 [P] Test pytest `backend/tests/integration/test_alembic_f55_migration.py` qui exécute `alembic upgrade head` puis `alembic downgrade -1` puis `alembic upgrade head` et vérifie via `psql` que les colonnes existent puis disparaissent puis réapparaissent (réversibilité).

### Types Pydantic + état partagé

- [ ] T012 [P] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/state.py` avec :
  - `ToolCategory` StrEnum (`ASK`, `SHOW`, `MUTATION`, `READ`).
  - Champs ajoutés à `AgentState` : `tool_calls_count_in_turn: int = 0`, `dry_run: bool = False`, `pending_confirmations: dict[str, PendingConfirmation] = {}`.
  - `PendingConfirmation` BaseModel (`extra='forbid'`) : `tool_call_id`, `tool_name`, `arguments`, `expires_at`.
  - `MutationResult` BaseModel (`extra='forbid'`).
  - `RateLimitDecision` BaseModel.
  - `ToolDispatchResult` enrichie : champs `kind`, `entity_type`, `entity_id`, `audit_log_id`, `fields_updated`, `is_dry_run`, `model_validator` cohérence kind/champs.
- [ ] T013 [P] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/mutation_ctx.py` exposant `MutationCtx` frozen dataclass (cf. data-model.md §2.3).
- [ ] T014 [P] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/sse.py` exposant `format_event(event_type, data, *, id=None, dry_run=False) -> str` (cf. research.md D6).
- [ ] T015 [P] Tests unit `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/unit/test_sse_format.py` : vérifier le formatage `event:`/`data:`/`\n\n`, l'ID optionnel, et le préfixe `dry_run:`.

### Registry catégorie + fail-fast au boot

- [ ] T020 Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/orchestrator/tool_registry.py` : ajouter le champ `category: ToolCategory` à `ToolDef` (NON null). Renseigner les valeurs pour TOUS les tools déjà enregistrés (fixtures_tools.py + tools registrants F15/F16/F17). Pour les tools non encore migrés, utiliser une valeur par défaut basée sur leur préfixe (`ask_*` → ASK, `show_*` → SHOW, `update_/create_/delete_/generate_/recompute_/attach_/revoke_` → MUTATION, `cite_/search_/recall_/flag_unsourced` → READ).
- [ ] T021 Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/mutation_handlers.py` exposant le décorateur `@mutation_handler(tool_name, *, requires_confirmation=False)` qui peuple `MUTATION_HANDLERS: dict[str, Handler]`. Inclure `ensure_handlers_registered()` appelé au startup_event qui vérifie qu'un handler existe pour chaque tool MUTATION et qu'aucun tool n'a `category=None` ; sinon `RuntimeError`.
- [ ] T022 Brancher `ensure_handlers_registered()` dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/main.py` via un `@app.on_event("startup")` ajouté en fin de fichier (additif, pas de modif des lignes existantes).
- [ ] T023 [P] Test unit `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/unit/test_boot_fail_fast.py` : (a) tool MUTATION sans handler → `RuntimeError`, (b) tool sans category → `RuntimeError`, (c) state propre → no raise.

**Checkpoint** : Foundation prête → User stories peuvent démarrer.

---

## Phase 3: User Story 1 — Mutation pilotée par le LLM avec audit complet (Priority: P1) 🎯 MVP

**Goal** : permettre à l'agent d'exécuter `update_company_profile`, `create_project`, `update_project` (non destructif) avec audit_log automatique, EventBus, sync front. C'est le coeur de la promesse produit.

**Independent Test** : envoyer `Mets à jour mon secteur, c'est de la boulangerie pâtisserie` via le chat → vérifier audit_log + sync Profil.

### Tests for User Story 1

- [ ] T030 [P] [US1] Test E2E backend pytest+httpx `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/e2e/test_chat_mutation_e2e.py` qui simule un POST `/api/chat/stream` avec un fake LLM renvoyant un tool_call `update_company_profile`, consomme le SSE, vérifie audit_log + EventBus publish.
- [ ] T031 [P] [US1] Test integration `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_dispatch_mutation_audit.py` qui appelle directement `dispatch(call, state, db, mutation_ctx)`, vérifie : (1) UPDATE business commit, (2) audit_log row créé avec `source_of_change='llm'` + `tool_call_id` + `agent_run_id`, (3) tool_call_log.status='ok', (4) une exception côté handler rollback la transaction (audit_log absent, business intact).
- [ ] T032 [P] [US1] Test integration `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_dispatch_rls_isolation.py` qui force un account A à invoquer `update_project(id=P_B.id)` → assert `kind='error', error_summary='entity_not_found'`, audit_log côté B vide.
- [ ] T033 [P] [US1] Test Playwright `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/chat-mutation-sync.spec.ts` qui : (1) ouvre `/profile/entreprise`, (2) ouvre `/chat`, (3) envoie un message qui force `update_company_profile`, (4) revient sur `/profile/entreprise` → champ secteur synchronisé sans rechargement.

### Implementation for User Story 1

- [ ] T040 [P] [US1] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/dispatcher.py` exposant `async def dispatch(...)` selon le contract dispatcher-api.md. Couvrir : routing par catégorie, instanciation `MutationCtx`, ouverture transaction DB avec `SET LOCAL "app.current_account_id"`, appel handler, append audit, EventBus publish, COMMIT (ou ROLLBACK si dry_run).
- [ ] T041 [P] [US1] Créer le module handlers `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/handlers/__init__.py` et y enregistrer les handlers décorés `@mutation_handler` pour `update_company_profile`, `create_project`, `update_project` (non destructifs). Chaque handler appelle le service métier existant (cf. `app/entreprise/service.py`, `app/projets/service.py`) en LECTURE SEULE pour ne pas conflicter avec F54 — F54 ne touche pas ces services en écriture.
- [ ] T042 [US1] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/audit/service.py` avec `append_diff(account_id, user_id, entity_type, entity_id, diffs, *, source_of_change, tool_call_id=None, agent_run_id=None)` qui INSERT une ligne audit_log avec les nouvelles colonnes. Garder backward compat (kwargs optionnels).
- [ ] T043 [US1] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/nodes/dispatch_tool.py` (squelette F53) pour appeler `dispatcher.dispatch(...)` au lieu du `_DB_HANDLERS` legacy. Conserver compat F53 via `_clear_handlers_for_tests()`.
- [ ] T044 [US1] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/sse_bridge.py` pour émettre `mutation` (payload incluant `entity_type`, `entity_id`, `fields_updated`, `audit_log_id`, `snapshot`, `message_id`) et `tool_call_completed` (admin only flag) selon contracts/sse-events.md.
- [ ] T045 [US1] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/runner.py` : consommer `astream_events(version='v2')`, mapper events → frames SSE via `format_event` + `sse_bridge`. Inclure le `text_delta` (LangChain `on_chat_model_stream`), `tool_call_started`, `mutation`, `tool_call_completed`, `error`, `message_done`.
- [ ] T046 [US1] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/llm_stream.py` pour brancher l'agent F53→F55 sur l'endpoint `/api/chat/stream` ; remplacer le proxy LLM brut par un appel au runner.
- [ ] T047 [US1] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/api.py` : endpoint `POST /api/chat/stream` retourne `StreamingResponse(content=runner.run_sse(...), media_type='text/event-stream')`. Header `X-Accel-Buffering: no` pour désactiver le buffering Nginx.
- [ ] T048 [P] [US1] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/app/composables/useChatStream.ts` : ajouter handlers pour `mutation`, `tool_call_completed` (filtré admin), `message_done` ; émettre `useChatEventBus().emit('entity_updated', ...)` quand un event `mutation` arrive.
- [ ] T049 [P] [US1] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/app/composables/useChatToolBridge.ts` qui consomme les events SSE poussés par `useChatStream` et route vers bottom sheet (ASK), viz inline (SHOW), EventBus (mutation).
- [ ] T050 [P] [US1] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/app/stores/chat.ts` : ajouter `pendingToolCalls`, `pendingViz`, `mutationPublishes`, mutations Pinia pour ces collections.
- [ ] T051 [P] [US1] Tests unit Vitest `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/unit/useChatStream.test.ts` (réception et routage events `mutation`).
- [ ] T052 [P] [US1] Tests unit Vitest `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/unit/useChatToolBridge.test.ts` (routage ASK→sheet, SHOW→viz, mutation→bus).
- [ ] T053 [P] [US1] Tests unit Vitest `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/unit/stores/chat.test.ts`.

**Checkpoint** : US1 fonctionnelle et testable indépendamment. À valider avant US2.

---

## Phase 4: User Story 2 — Bottom sheet (ASK) et viz inline (SHOW) (Priority: P1)

**Goal** : flux ASK/SHOW complet : tool_invoke SSE → bottom sheet F39 ou viz F40 inline → réponse user retournée au tour suivant.

**Independent Test** : envoyer un message qui force `ask_qcu` puis `show_radar_chart` → vérifier ouverture sheet + render viz.

### Tests for User Story 2

- [ ] T060 [P] [US2] Test integration `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_dispatch_ask_show.py` : (1) dispatch `ask_qcu` → `kind='frontend_event'`, output contient `arguments`, AUCUNE mutation DB ; (2) dispatch `show_radar_chart` → idem.
- [ ] T061 [P] [US2] Test Playwright `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/chat-bottom-sheet.spec.ts` : envoyer un message → vérifier ouverture bottom sheet (rôle `dialog`, animation gsap), valider une option, vérifier que le tour suivant s'enchaîne correctement.

### Implementation for User Story 2

- [ ] T070 [US2] Patcher `dispatcher.dispatch(...)` (déjà créé en T040) pour gérer ASK/SHOW : retourner `kind='frontend_event'` avec payload validé sans toucher DB ; mesurer latence sous 5 ms (NFR-001).
- [ ] T071 [US2] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/sse_bridge.py` pour émettre `tool_invoke` avec `category` (ASK/SHOW) et `arguments` validés.
- [ ] T072 [US2] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/app/components/chat/MessageBubble.vue` pour rendre le composant viz F40 (`<VizRenderer>`) inline pour les SHOW. La bulle reste display-only pour les ASK (pas d'input).
- [ ] T073 [US2] Brancher `useChatToolBridge.ts` (créé en T049) sur `useChatBottomSheet().open(tool_name, payload)` quand `tool_invoke.category === 'ASK'`.
- [ ] T074 [US2] Patcher `useChatBottomSheet` (existant F39) pour accepter le retour utilisateur et le re-poster comme `sheet_result` au prochain tour LLM via `chat.sendSheetResult(tool_call_id, value)`.

**Checkpoint** : US2 fonctionnelle (P10 respecté).

---

## Phase 5: User Story 3 — Confirmation pour mutations destructives (Priority: P1)

**Goal** : `delete_*` et tools `requires_confirmation=True` ne s'exécutent jamais sans confirmation user explicite + TTL 3 min.

**Independent Test** : envoyer `supprime ce projet` → bottom sheet ask_yes_no → cliquer "Non" → projet intact.

### Tests for User Story 3

- [ ] T080 [P] [US3] Test integration `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_dispatch_confirmation_yesno.py` : (1) appel `delete_project` → `kind='frontend_event', status='pending_confirmation'`, pending_confirmation stocké ; (2) tour suivant avec réponse "no" → `tool_call_log.status='cancelled_by_user'`, projet intact ; (3) tour avec réponse "yes" → call ré-exécuté ; (4) >180 s → `confirmation_expired`.
- [ ] T081 [P] [US3] Test unit `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/unit/test_confirmation_flow.py` : isolation des fonctions `store_pending_confirmation` / `consume_confirmation`.

### Implementation for User Story 3

- [ ] T090 [P] [US3] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/confirmation.py` exposant `store_pending_confirmation`, `consume_confirmation`, `is_expired` (TTL configurable via env `LLM_AGENT_CONFIRMATION_TTL_SECONDS=180`). Persistance JSONB dans `agent_run.metadata['pending_confirmations']`.
- [ ] T091 [US3] Patcher `dispatcher.dispatch(...)` pour : (1) si `tool_def.requires_confirmation=True` ET pas de confirmation entrante → `store_pending_confirmation` + retour `frontend_event`/`pending_confirmation` ; (2) sinon vérifier la confirmation reçue, exécuter ou annuler.
- [ ] T092 [US3] Enregistrer un handler décoré `@mutation_handler('delete_project', requires_confirmation=True)` dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/handlers/__init__.py`.
- [ ] T093 [US3] Frontend : patcher `useChatToolBridge.ts` pour gérer le retour user "Yes/No" et le re-poster en `sheet_result` typed `confirmation_response`. Ajouter une vue `BottomSheet` template confirmation dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/app/components/chat/BottomSheetConfirmation.vue` (template présentant le récap clair).

**Checkpoint** : US3 fonctionnelle. Edge cases TTL et "Non" couverts.

---

## Phase 6: User Story 4 — Rate limit anti-runaway et idempotence (Priority: P1)

**Goal** : empêcher 31 mutations/min, fail-safe si store down, idempotence DB-backed sur reconnexion SSE.

**Independent Test** : test pytest qui simule 31 calls + test idempotence replay.

### Tests for User Story 4

- [ ] T100 [P] [US4] Test integration `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_dispatch_rate_limit_31.py` : 31 calls `update_company_profile` en < 60 s → 30 ok + 1 `rate_limited` + SSE `error` émis.
- [ ] T101 [P] [US4] Test integration `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_dispatch_idempotency_replay.py` : 2 dispatch même `(account, agent_run, call_id)` → 1 row business, 2e retourne le même `ToolDispatchResult` ; deux accounts différents avec même hash → 2 rows business, pas de conflit.
- [ ] T102 [P] [US4] Test unit `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/unit/test_rate_limit_inmemory.py` : fenêtre glissante 60 s, bounded LRU 1000 keys, fail-safe quand store inaccessible (mock raise).
- [ ] T103 [P] [US4] Test unit `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/unit/test_idempotency.py` : compute_idempotency_key déterministe, find_existing reconstruit ToolDispatchResult depuis row.

### Implementation for User Story 4

- [ ] T110 [P] [US4] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/rate_limit.py` exposant `RateLimitStore` Protocol + `InMemoryRateLimitStore` (asyncio.Lock + bounded LRU 1000 keys, fenêtre glissante 60 s) + `RedisRateLimitStore` stub (Lua script INCR+EXPIRE atomique). Sélection au boot via `LLM_AGENT_RATE_LIMIT_BACKEND` env.
- [ ] T111 [P] [US4] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/idempotency.py` exposant `compute_idempotency_key`, `find_existing(db, account_id, key)` (SELECT FOR SHARE), `reconstruct_result(row)`.
- [ ] T112 [US4] Patcher `dispatcher.dispatch(...)` pour : (1) idempotency check au début, (2) rate_limit.check_and_increment avant exécution mutation, (3) fail-safe si `RateLimitDecision.reason == 'store_unavailable'` → refuser la mutation avec `kind='error', status='error', error_summary='rate_limit_unavailable'`.
- [ ] T113 [P] [US4] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/app/composables/useChatStream.ts` pour rendre le code SSE `error` poliment dans la bulle (existant F41) avec message custom "Trop de modifications successives, ralentissons" si `code='rate_limited'`.

**Checkpoint** : US4 fonctionnelle. Stress test 31/60s passe.

---

## Phase 7: User Story 5 — READ tool ré-injecté au LLM (Priority: P1)

**Goal** : `recall_history`, `cite_source`, `search_source` retournent leur résultat sérialisé qui est ré-injecté en `ToolMessage` LangChain au tour suivant.

**Independent Test** : invoquer `recall_history` via fake LLM, vérifier ToolMessage injecté.

### Tests for User Story 5

- [ ] T120 [P] [US5] Test integration `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_dispatch_read_reinject.py` : dispatch `recall_history(query="scoring")` → kind='tool_message', output['content'] = JSON tronqué <= budget tokens, et le runner re-soumet un ToolMessage au LLM.
- [ ] T121 [P] [US5] Test unit `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/unit/test_read_serializer.py` : troncature au budget tokens, JSON structuré valide, top-N items.
- [ ] T122 [P] [US5] Test integration `backend/tests/integration/test_dispatch_hard_cap_10.py` : 11 dispatch READ dans le même tour → forcer `compose_response` avec fallback texte.

### Implementation for User Story 5

- [ ] T130 [P] [US5] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/read_serializer.py` avec `serialize_read_result(payload, budget_tokens=1500) -> str` (JSON structuré tronqué, count tokens via heuristique 4 chars/token).
- [ ] T131 [US5] Patcher `dispatcher.dispatch(...)` pour catégorie READ : appeler handler READ (registry parallèle `_REINVOKE_HANDLERS` F53), sérialiser via read_serializer, retourner `kind='tool_message'`.
- [ ] T132 [US5] Patcher `nodes/dispatch_tool.py` pour injecter le résultat READ en `ToolMessage` LangChain comme déjà prévu en F53, et incrémenter `state.tool_calls_count_in_turn`.
- [ ] T133 [US5] Patcher `runner.py` pour respecter le hard cap 10 tool calls par tour (FR-015) ; au-delà, forcer route vers `compose_response`.

**Checkpoint** : US5 fonctionnelle. Loops READ infinies coupées au cap 10.

---

## Phase 8: User Story 6 — Mode dry_run admin (Priority: P2)

**Goal** : admin peut activer `dry_run=True`, mutations simulées sans toucher DB ni audit, events SSE préfixés `dry_run:`.

**Independent Test** : curl avec header `X-Agent-DryRun: true` (admin token) → vérifier 0 row business, 0 audit, frame SSE préfixée.

### Tests for User Story 6

- [ ] T140 [P] [US6] Test integration `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_dispatch_dry_run_admin.py` : (1) admin avec dry_run=True → mutation simulée, 0 audit, 0 row business, SSE `dry_run:mutation` ; (2) PME avec dry_run=True → 403.

### Implementation for User Story 6

- [ ] T150 [US6] Patcher `dispatcher.dispatch(...)` : si `dry_run=True`, ouvrir transaction puis ROLLBACK forcé, ne pas appeler `audit_logger.append_many`, ne pas publier EventBus, set `is_dry_run=True` sur le ToolDispatchResult.
- [ ] T151 [US6] Patcher `runner.py` + `sse_bridge.py` pour préfixer `dry_run:` sur les event_type quand `state.dry_run=True`.
- [ ] T152 [US6] Patcher `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/api.py` pour lire le header `X-Agent-DryRun` et l'autoriser uniquement si `current_user.role == 'admin'` ; sinon 403.
- [ ] T153 [P] [US6] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/app/components/chat/DryRunBanner.vue` (bandeau jaune "Mode simulation actif"), affiché conditionnellement dans `chat.dryRunActive`.
- [ ] T154 [P] [US6] Patcher `useChatStream.ts` pour détecter le préfixe `dry_run:` et toggle `chat.dryRunActive`.

**Checkpoint** : US6 fonctionnelle pour admins.

---

## Phase 9: User Story 7 — Hooks pre/post dispatch (Priority: P2)

**Goal** : permettre aux devs d'enregistrer des hooks `before_dispatch` / `after_dispatch` (telemetry, A/B) sans modifier les handlers.

**Independent Test** : enregistrer un hook trivial (compteur), exécuter une mutation, vérifier compteur incrémenté.

### Tests for User Story 7

- [ ] T160 [P] [US7] Test unit `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/unit/test_dispatcher_hooks.py` : (1) before_hook reçoit (call, state) avant handler, (2) after_hook reçoit (call, result) après, (3) exception dans hook absorbée + log warning, (4) ordre d'enregistrement respecté.

### Implementation for User Story 7

- [ ] T170 [US7] Patcher `dispatcher.py` pour exposer `@before_dispatch`, `@after_dispatch` décorateurs et appeler les hooks dans `dispatch(...)` (best-effort, exceptions absorbées via try/except + logger.warning).

**Checkpoint** : US7 fonctionnelle, hooks observables.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose** : finitions, observabilité, doc dev, validation finale.

- [ ] T200 [P] Documentation dev : créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/README.md` (architecture dispatcher, séquence dispatch, exemples handlers).
- [ ] T201 [P] Mise à jour de `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/alembic/README.md` avec les colonnes ajoutées par F55.
- [ ] T202 Vérifier la couverture pytest globale ≥ 80 % et ≥ 90 % sur `app/agent/dispatcher.py`, `app/agent/mutation_ctx.py`, `app/agent/rate_limit.py`, `app/agent/idempotency.py`, `app/agent/confirmation.py`. Si en dessous : compléter les tests unitaires.
- [ ] T203 Vérifier la couverture frontend ≥ 80 % sur `useChatStream`, `useChatToolBridge`, `stores/chat`. Si en dessous : compléter Vitest.
- [ ] T204 [P] Lint backend (`make lint` côté backend `ruff check .`) et frontend (`pnpm lint`). Aucune erreur autorisée.
- [ ] T205 [P] Run quickstart.md manuel : valider §4.1 à §4.7 sur le dev local.
- [ ] T206 Re-vérifier les 10 gates Constitution Check du plan.md (P1..P10). Tous doivent rester ✅.
- [ ] T207 [P] Vérifier qu'aucun `print(`/`console.log(` n'est en prod (rules/python/hooks.md + rules/typescript équivalent).
- [ ] T208 [P] Vérifier que tous les fichiers nouveaux (dispatcher.py, mutation_ctx.py, rate_limit.py, idempotency.py, confirmation.py, sse.py, useChatToolBridge.ts) sont < 400 lignes et fonctions < 50 lignes (rules/common/coding-style.md).
- [ ] T209 Final : exécuter `pytest -m 'not perf' --cov=app/agent --cov-report=term-missing` + `pnpm vitest run` + `pnpm playwright test` ; tous verts.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** : aucune dépendance.
- **Foundational (Phase 2)** : dépend de Setup. BLOQUE toutes les US.
- **US1 (Phase 3)** : dépend de Foundational. MVP critique.
- **US2 (Phase 4)** : dépend de Foundational. Indépendante d'US1 (test isolé) mais utilise les composants ASK/SHOW partagés. Peut être démarrée en parallèle de US1 par un autre dev.
- **US3 (Phase 5)** : dépend de Foundational + US1 (handler `delete_project` réutilise infra mutation handlers). Démarrer après US1.
- **US4 (Phase 6)** : dépend de Foundational + US1 (rate_limit/idempotency injectés dans dispatcher). Démarrer après US1.
- **US5 (Phase 7)** : dépend de Foundational. Indépendante d'US1-4 sauf le hard cap qui partage `state.tool_calls_count_in_turn`.
- **US6 (Phase 8)** : dépend de Foundational + US1 (dry_run patche le dispatcher).
- **US7 (Phase 9)** : dépend de Foundational + US1 (hooks dans dispatcher).
- **Polish (Phase N)** : après toutes les US qu'on souhaite livrer.

### User Story Dependencies

- **US1 (P1)** : prérequis P2 → ensuite. Indépendant des autres US (via `mutation_handlers` injectables et fakellm fixture).
- **US2 (P1)** : peut tourner en parallèle de US1 si dev dédié frontend.
- **US3 (P1)** : intègre US1 (réutilise mutation_handler infra).
- **US4 (P1)** : intègre US1 (rate_limit + idempotency injectés dans dispatch).
- **US5 (P1)** : indépendante.
- **US6 (P2)** : intègre US1 (dry_run patche dispatch).
- **US7 (P2)** : intègre US1 (hooks dans dispatch).

### Within Each User Story

- Tests E2E backend + Playwright frontend FIRST (RED).
- Implémentation backend (handlers, dispatcher) → frontend (composables, stores) → tests verts.
- Lint après chaque fichier modifié (PostToolUse hook ruff/eslint).
- Commit après chaque US validée (mais l'orchestrateur série gère le commit/push final).

### Parallel Opportunities

- T011..T015 (tests unit + sse + state) en parallèle de T010 (migration alembic) car fichiers différents.
- T020..T023 (registry + boot fail-fast) après T010.
- US1 et US2 peuvent être faites en parallèle si un dev backend et un dev frontend.
- T040 (dispatcher.py) et T041 (handlers) peuvent être écrits en // si dispatcher consomme l'interface du registry.
- T048..T053 (frontend US1) en // de T040..T047 (backend US1).
- T080..T093, T100..T113, T140..T154, T160..T170 : chaque US a ses propres fichiers tests → tous parallélisables après foundational.
- Tous les T200..T209 (Polish) en parallèle.

---

## Parallel Example: Foundational (Phase 2)

```bash
# Lancer tous les types Pydantic en parallèle (fichiers différents) :
Task: "T012 [P] Étendre app/agent/state.py avec ToolCategory + extensions AgentState"
Task: "T013 [P] Créer app/agent/mutation_ctx.py"
Task: "T014 [P] Créer app/agent/sse.py"
Task: "T015 [P] Tests unit test_sse_format.py"
```

## Parallel Example: User Story 1 (after Foundational)

```bash
Task: "T030 [P] [US1] Test E2E backend test_chat_mutation_e2e.py"
Task: "T031 [P] [US1] Test integration test_dispatch_mutation_audit.py"
Task: "T032 [P] [US1] Test integration test_dispatch_rls_isolation.py"
Task: "T033 [P] [US1] Test Playwright chat-mutation-sync.spec.ts"
Task: "T040 [P] [US1] dispatcher.py"
Task: "T041 [P] [US1] handlers/__init__.py"
Task: "T048 [P] [US1] frontend useChatStream patches"
Task: "T049 [P] [US1] useChatToolBridge.ts"
Task: "T050 [P] [US1] stores/chat.ts patches"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3 + US4 + US5 — toutes P1 sont MVP)

1. Phase 1 Setup.
2. Phase 2 Foundational (BLOQUANT).
3. Phase 3 US1 (mutation + audit + sync). STOP & VALIDATE quickstart §4.3.
4. Phase 4 US2 (ASK/SHOW). STOP & VALIDATE §4.1, §4.2.
5. Phase 5 US3 (confirmation). STOP & VALIDATE §4.4.
6. Phase 6 US4 (rate-limit + idempotence). STOP & VALIDATE §4.5, §4.6.
7. Phase 7 US5 (READ ré-injection). STOP & VALIDATE.
8. Polish global.

US6 et US7 (P2) peuvent être livrées dans une 2e itération si pression de planning.

### Incremental Delivery

- Foundational ready → MVP démontrable en commit US1.
- Chaque US ajoute une capacité sans casser la précédente.
- À l'issue de US4, la plateforme est productive (rate-limit + idempotence garantissent la prod).

### Parallel Team Strategy

- 2 devs : Dev A backend (US1 → US3 → US4 → US5), Dev B frontend (T048..T053, T070..T074, T093, T154 + Playwright).
- 3 devs : Dev A backend US1+US3, Dev B backend US4+US5, Dev C frontend.

---

## Notes

- [P] tasks = fichiers différents, pas de dépendance non terminée.
- [Story] label maps task → user story (traçabilité).
- Vérifier que les tests rouges → verts (TDD).
- Les modifications de `app/main.py`, `app/config.py`, `pyproject.toml` sont des **ajouts seuls** (pas de modif des lignes existantes — F54 tourne en //).
- F54 ne doit pas être touchée : `app/agent/nodes/build_context.py`, `app/agent/nodes/recall_memory.py`, `app/agent/context/*`, `app/entreprise/`, `app/projets/` (lecture seule), `app/candidatures/`, `app/scoring/`.
- Le commit + push est laissé à l'orchestrateur série, pas à F55.
