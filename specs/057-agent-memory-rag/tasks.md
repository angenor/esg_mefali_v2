---

description: "Tasks F57 — Agent Memory & Long-term Recall (LangGraph + pgvector RAG)"
---

# Tasks: Agent Memory & Long-term Recall (F57)

**Input**: Design documents from `/specs/057-agent-memory-rag/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: TDD-first (RED → GREEN → REFACTOR), conforme constitution P9 et règle `.claude/rules/common/testing.md`. Coverage cible ≥ 90 % sur `app/agent/memory/*` et `app/agent/nodes/recall_memory.py` ; ≥ 80 % global (gate `fail_under = 80` dans `backend/pyproject.toml`).

**Organization**: Tasks groupées par user story (US1-US9) afin que chaque story soit indépendamment testable et livrable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallélisable (fichiers différents, pas de dépendance non terminée)
- **[Story]**: story attachée (US1-US9)
- Chemin de fichier ABSOLU obligatoire

## Path conventions

- Backend Python : `backend/app/...` et `backend/tests/...`
- Frontend Nuxt : `frontend/app/...` et `frontend/tests/...`
- Migrations : `backend/alembic/versions/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Préparer l'environnement F57 (variables d'env, packages skeletons).

- [ ] T001 [P] Ajouter les variables d'env F57 dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/config.py` (FR-013) : `LLM_AGENT_MEMORY_TOP_K=3`, `LLM_AGENT_MEMORY_THRESHOLD=0.7`, `LLM_AGENT_MEMORY_RECENT_COUNT=15`, `LLM_AGENT_COMPACT_THRESHOLD=100`, `LLM_AGENT_COMPACT_BATCH_SIZE=50`, `LLM_AGENT_COMPACT_MAX_TOKENS=500`, `LLM_AGENT_ENTITY_MEMORY_MAX_TOKENS=800`, `LLM_AGENT_RECALL_HISTORY_MAX_TOKENS=800`, `LLM_AGENT_RECALL_LOG_RETENTION_DAYS=90`. Validation Pydantic settings (échec FAST si valeurs invalides).
- [ ] T002 [P] Documenter dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/.env.example` les nouvelles variables F57 (mêmes valeurs default que T001).
- [ ] T003 [P] Créer le package skeleton `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/memory/__init__.py` (vide pour l'instant, étendu par US1+).
- [ ] T004 [P] Vérifier que `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/embeddings_client.py` existe et expose `async def embed(text: str) -> list[float]`. Si absent ou interface différente, harmoniser (extension non destructive).
- [ ] T005 Ajouter dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/embeddings_client.py` un guard `assert len(vec) == 1024` après chaque call Voyage + un helper `def hash_query(query: str) -> str` (SHA-256 hex), réutilisé par cache et recall_log.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schéma DB + tests RLS/audit foundational. AUCUNE user story ne peut commencer sans cette phase.

**⚠️ CRITICAL**: bloque toutes les user stories.

### Tests foundational (TDD-first, RED first)

- [ ] T006 [P] Écrire test RLS `agent_entity_memory` dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_rls_entity_memory.py` : INSERT avec `account_id=A`, SET `app.current_account_id=B`, SELECT doit retourner 0 row (cross-tenant, P2). Doit ÉCHOUER tant que la migration n'est pas appliquée.
- [ ] T007 [P] Écrire test RLS `recall_log` dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_rls_recall_log.py` : INSERT account_id=A, GUC=B, SELECT 0 row + UPDATE/DELETE révoqués pour applicative role (P3 append-only). Doit ÉCHOUER tant que migration absente.
- [ ] T008 [P] Écrire test schema `chat_thread.summary` + `chat_thread.last_compacted_at` + `chat_message.compacted` dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_schema_extensions.py` : verify columns exist with expected types/defaults. Doit ÉCHOUER avant migration.

### Migration & ORM

- [ ] T009 Créer migration Alembic `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/alembic/versions/0036_f57_memory_rag.py` (cible 0036, renumérotation possible si F56 prend 0035 — `down_revision` ajusté au merge). Operations : ADD COLUMN `chat_thread.summary TEXT NULL`, `chat_thread.last_compacted_at TIMESTAMPTZ NULL`, ADD COLUMN `chat_message.compacted BOOL NOT NULL DEFAULT FALSE`, CREATE TABLE `agent_entity_memory` (cf. data-model.md §2.1) avec UNIQUE + RLS policy + audit trigger, CREATE TABLE `recall_log` (cf. data-model.md §2.2) avec INDEX + RLS policy + REVOKE UPDATE/DELETE on applicative role, CREATE INDEX `chat_message_embedding_hnsw_idx` HNSW (m=16, ef_construction=64). Downgrade reverse.
- [ ] T010 [P] Créer ORM models dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/memory/models.py` : `AgentEntityMemory`, `RecallLog` (cf. data-model.md §4.1).
- [ ] T011 Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/memory/repository.py` (existant F18) avec helpers `get_or_create_entity_memory`, `purge_thread_embeddings`, `get_entities_referenced(thread_id)` (RLS-aware, query `chat_message.metadata->'entity_refs'`).
- [ ] T012 Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/memory/schemas.py` avec `EntityRef`, `MemorySnapshotV2` (cf. data-model.md §4.2). Backwards-compatible.
- [ ] T013 [P] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/state.py` (existant F53) — AJOUT MINIMAL des champs transient `embedding_cache: dict[str, list[float]] = Field(default_factory=dict, exclude=True)` et `recall_log_entries: list[dict] = Field(default_factory=list, exclude=True)`. Vérifier que le checkpointer F53 ignore ces champs.
- [ ] T014 Lancer `make migrate` et faire passer les tests T006/T007/T008 (transition RED→GREEN). Vérifier `recall_log` UPDATE/DELETE bien révoqués pour le rôle applicatif.

**Checkpoint** : Foundation prête → user stories peuvent commencer.

---

## Phase 3: User Story 1 — Recall automatique court+long terme (Priority: P1) 🎯 MVP

**Goal**: Le nœud `recall_memory` charge les 15 derniers messages chronologiques + top-K=3 messages anciens via cosine search pgvector, insérés en tête avec préfixe explicite.

**Independent Test**: Thread 50 msgs avec mention "solaire 50 kWc" dans msgs 1-10 uniquement → query "Reprends le solaire 50 kWc" → contexte LLM contient 15 derniers + 3 souvenirs préfixés ; réponse cite chiffres anciens.

### Tests for User Story 1 (RED first)

- [ ] T015 [P] [US1] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_recall_auto.py` couvrant : (a) thread 5 msgs → pas d'embed call, pas de recall_log auto entry ; (b) thread 50 msgs avec mention solaire au début → 15 derniers + 3 souvenirs ≥ 0.7, 1 recall_log entry ; (c) thread 100 msgs sans match au-dessus du seuil → seuls 15 derniers, 0 souvenirs ; (d) Voyage API mock down → fallback dégradé sans 500 ; (e) test format des messages insérés (préfixe `[Souvenirs pertinents d'échanges précédents]`). Tests RED initiaux.

### Implementation for User Story 1

- [ ] T016 [P] [US1] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/memory/embedding_cache.py` : `async def get_or_compute(state: AgentState, thread_id: UUID, query: str) -> list[float]`. Clé cache `f"{thread_id}:{hash_query(query)}"`. Réutilise `embeddings_client.embed()`.
- [ ] T017 [P] [US1] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/memory/long_term.py` : `async def search_long_term(thread_id, account_id, query_embedding, exclude_message_ids, limit, threshold, db) -> list[ChatMessage]`. Cosine search via pgvector `<=>` operator, scope strict `thread_id` + `account_id`, exclut `compacted=True`. RLS implicit via current_setting GUC.
- [ ] T018 [P] [US1] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/memory/recall_log.py` : `async def write_recall_log(db, agent_run_id, account_id, thread_id, recall_type, query_hash, top_k, top_scores, latency_ms) -> None`. INSERT only (UPDATE/DELETE bloqués par RLS).
- [ ] T019 [US1] **RÉÉCRIRE TOTALEMENT** `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/nodes/recall_memory.py` (livré squelette F54) : implémenter logique US1 (15 derniers + recall long terme + summary block si présent + insertion préfixée). Mode dégradé si Voyage/pgvector down. Écrire `state.recall_log_entries` (flush en fin de tour, pas in-line). Conforme contracts/recall-memory-node.md.
- [ ] T020 [US1] Hook le flush des `recall_log_entries` à la fin du tour LangGraph : modifier `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/runner.py` ou `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/graph.py` (existants F53) pour écrire les entries en DB après la dernière node (1 seul commit par tour).
- [ ] T021 [US1] Faire passer T015 (RED→GREEN). Vérifier coverage ≥ 90 % sur `app/agent/memory/long_term.py`, `app/agent/memory/embedding_cache.py`, `app/agent/memory/recall_log.py`, `app/agent/nodes/recall_memory.py`.

**Checkpoint**: User Story 1 fonctionnelle ; recall automatique au début du tour est opérationnel.

---

## Phase 4: User Story 2 — Tool `recall_history(query)` invocable explicitement (Priority: P1)

**Goal**: Le LLM peut invoquer `recall_history(query, limit)` via le dispatcher F55 (catégorie READ) ; cosine search scope thread courant ; ré-injection ToolMessage.

**Independent Test**: LLM produit `recall_history(query="budget", limit=5)` → dispatcher exécute, cosine search retourne max 5 messages, ToolMessage tronqué selon budget tokens injecté au tour suivant.

### Tests for User Story 2 (RED first)

- [ ] T022 [P] [US2] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_recall_history_tool.py` : (a) call valide retourne 5 matches ; (b) `query=""` rejeté validateur ; (c) `limit=20` rejeté ; (d) `extra={"foo":"bar"}` rejeté (`extra='forbid'`) ; (e) cache hit si recall auto a calculé l'embedding du même query dans le même tour (1 seul appel Voyage spy) ; (f) `recall_log` entry avec `recall_type='tool'` écrite. Tests P9 + NFR-008.

### Implementation for User Story 2

- [ ] T023 [US2] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/handlers/recall_history.py` : Pydantic `RecallHistoryArgs`, `RecallHistoryResult`, `RecallHistoryMatch` (cf. contracts/recall-history-tool.md). Docstring use when / don't use when. `async def handle_recall_history(args, ctx) -> RecallHistoryResult` réutilise `embedding_cache.get_or_compute` + `long_term.search_long_term` + `recall_log.write_recall_log` + tronquage selon `LLM_AGENT_RECALL_HISTORY_MAX_TOKENS`.
- [ ] T024 [US2] Enregistrer le tool dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/tool_factory.py` (existant F55) — AJOUT MINIMAL : import `RecallHistoryArgs` + handler, déclaration `ToolDef(name='recall_history', category=ToolCategory.READ, args=RecallHistoryArgs, handler=handle_recall_history, ...)`. Ne pas modifier les déclarations existantes.
- [ ] T025 [US2] Faire passer T022 (RED→GREEN). Spy Voyage embed call count ≤ 1 par tour validé.

**Checkpoint**: Tool `recall_history` LLM-callable disponible. US1+US2 fonctionnels.

---

## Phase 5: User Story 3 — Memory snapshot endpoint enrichi (Priority: P1)

**Goal**: `GET /me/chat/threads/{id}/memory` retourne `MemorySnapshotV2` (total, recent_count, summary, vector_index_size, last_compaction_at, entities_referenced).

**Independent Test**: thread 50 msgs / 25 indexés / compacté → GET retourne tous les champs ; cross-tenant retourne 404.

### Tests for User Story 3 (RED first)

- [ ] T026 [P] [US3] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_snapshot_endpoint.py` : (a) thread riche → tous les champs remplis ; (b) thread sans compaction → summary=null, last_compaction_at=null, no error ; (c) cross-tenant 404 ; (d) thread inexistant 404 ; (e) backwards-compat F18 (champs ajoutés, pas renommés).

### Implementation for User Story 3

- [ ] T027 [US3] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/memory/service.py` avec `async def get_memory_snapshot(thread_id, account_id, db) -> MemorySnapshotV2` : agrège `total_messages`, `recent_messages_count`, `summary`, `vector_index_size` (count where embedding IS NOT NULL), `last_compaction_at`, `entities_referenced` (via repository helper T011).
- [ ] T028 [US3] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/memory/api.py` (existant F18) — modifier la route `GET /me/chat/threads/{id}/memory` pour retourner `MemorySnapshotV2`. RLS via middleware F02. Cross-tenant ⇒ 404.
- [ ] T029 [US3] Faire passer T026 (RED→GREEN).

**Checkpoint**: GET endpoint enrichi opérationnel. US1+US2+US3 fonctionnels.

---

## Phase 6: User Story 4 — Forget RGPD synchrone (Priority: P1)

**Goal**: `DELETE /me/chat/threads/{id}/memory` purge embeddings + summary + last_compacted_at synchronously, écrit audit_log, sans toucher messages bruts ni entity_memory.

**Independent Test**: thread 50 msgs indexés/compactés → DELETE → 200 + embeddings NULL + summary NULL + audit_log + content intact + entity_memory inchangée.

### Tests for User Story 4 (RED first)

- [ ] T030 [P] [US4] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_forget_rgpd.py` : (a) DELETE classique → 200, embeddings purgés, summary cleared, audit_log entry, contents intacts ; (b) idempotent (deuxième DELETE → 200) ; (c) cross-tenant 404 ; (d) `agent_entity_memory` du compte INTACTE ; (e) compaction en cours sur même thread → DELETE attend lock ≤ 5 s ou refuse proprement.

### Implementation for User Story 4

- [ ] T031 [US4] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/memory/service.py` avec `async def forget_thread_memory(thread_id, account_id, user_id, db) -> ForgetMemoryResult` : transaction synchronisée — UPDATE chat_message SET embedding=NULL, UPDATE chat_thread SET summary=NULL/last_compacted_at=NULL, INSERT audit_log avec `source_of_change='memory_system'`. Retourne le compte d'embeddings purgés.
- [ ] T032 [US4] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/memory/api.py` avec route `DELETE /me/chat/threads/{id}/memory` (cf. contracts/memory-endpoint.md). Cross-tenant 404. Réponse 200 idempotent.
- [ ] T033 [US4] Faire passer T030 (RED→GREEN).

**Checkpoint**: Forget RGPD synchrone opérationnel. US1-US4 fonctionnels.

---

## Phase 7: User Story 5 — Anti-fuite cross-thread et cross-account (Priority: P1)

**Goal**: Toutes les requêtes mémoire scope strict `thread_id` + `account_id`. Aucun message d'un thread B dans le contexte d'un thread A.

**Independent Test**: 2 threads d'un même compte avec contenus distincts. Recall dans Thread B sur sujet uniquement présent dans Thread A → 0 message du Thread A apparaît.

### Tests for User Story 5 (RED first)

- [ ] T034 [P] [US5] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_cross_thread_isolation.py` : (a) Thread A (account X) "panneaux solaires" + Thread B (account X) "scooters", recall dans B sur "panneaux" → 0 result ; (b) Thread A account X / Thread B account Y, attempt scope Thread B depuis JWT account X → 404 RLS ; (c) `agent_entity_memory` (account X) accessible depuis nouveau Thread D du compte X (légitime account-scope) ; (d) cache embedding key inclut thread_id (no cross-thread cache leak).

### Implementation for User Story 5

- [ ] T035 [US5] Vérifier (audit code review) que `long_term.search_long_term`, `recall_history` handler, `compactors.compact_thread`, `entity_memory.update_entity_memory` filtrent TOUS par `thread_id = :thread_id AND account_id = :account_id` ou s'appuient sur RLS GUC + ajoute le filtre thread_id explicite. Adapter si nécessaire.
- [ ] T036 [US5] Vérifier que la clé du cache embedding T016 = `f"{thread_id}:{hash_query(query)}"` (défense en profondeur, pas seulement hash query brute).
- [ ] T037 [US5] Faire passer T034 (RED→GREEN). Auditer manuellement la couverture des paths memory pour scope thread_id.

**Checkpoint**: Anti-fuite vérifiée par tests. US1-US5 fonctionnels.

---

## Phase 8: User Story 6 — Compaction async des threads ≥ 100 messages (Priority: P2)

**Goal**: BackgroundTask déclenché à 100, 150, 200… messages, génère résumé ≤ 500 tokens via LLM, REMPLACE `chat_thread.summary`, marque chunks compacted=True. Lock optimiste.

**Independent Test**: insérer 100 msgs → BackgroundTask enqueué non bloquant → 5 s plus tard `summary` non null < 500 tokens, msgs 1-50 compacted=True, lock concurrence respecté.

### Tests for User Story 6 (RED first)

- [ ] T038 [P] [US6] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_compaction.py` : (a) thread 99 msgs → insert msg 100 → BackgroundTask enqueued non-blocking ; (b) compaction terminée < 5 s → `summary` < 500 tokens, msgs 1-50 compacted ; (c) deux compactions concurrentes → lock optimiste laisse passer 1 seule (test_concurrent_compaction_single_winner) ; (d) tour LLM suivant utilise summary + 15 derniers (compacted=True excluded) ; (e) audit_log entry pour la compaction.

### Implementation for User Story 6

- [ ] T039 [P] [US6] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/memory/compactors.py` : `async def compact_thread(thread_id, account_id, db) -> int` (cf. contracts ; lock optimiste UPDATE conditionnel cf. research.md R4 ; LLM call via `app.llm_client.get_chat_completion()` avec prompt système strict ; UPDATE summary + flag compacted=True ; audit_log).
- [ ] T040 [US6] Étendre `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/memory/service.py` `enqueue_compact_if_needed(thread_id, account_id, count, background_tasks)` : si `count >= LLM_AGENT_COMPACT_THRESHOLD AND count % LLM_AGENT_COMPACT_BATCH_SIZE == 0`, enqueue.
- [ ] T041 [US6] Hooker l'appel `enqueue_compact_if_needed` dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/chat/memory/api.py` (route POST messages, après l'INSERT message).
- [ ] T042 [US6] Faire passer T038 (RED→GREEN). Vérifier lock optimiste avec test concurrent.

**Checkpoint**: Compaction async opérationnelle. US1-US6 fonctionnels.

---

## Phase 9: User Story 7 — Persistance résumée par entité (Priority: P2)

**Goal**: Hook post-mutation dispatcher F55 enqueue update_entity_memory ; UPSERT agent_entity_memory ; DELETE on entity delete ; version++.

**Independent Test**: `update_company_profile(secteur="C10.71")` via dispatcher → 30 s plus tard, `agent_entity_memory(Entreprise, ...).summary` mentionne le nouveau secteur, version++.

### Tests for User Story 7 (RED first)

- [ ] T043 [P] [US7] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_entity_memory.py` : (a) mutation `update_company_profile` → BackgroundTask exécutée, agent_entity_memory créée v1 + audit_log ; (b) mutation suivante → version=2, summary remplacé ; (c) `delete_project` → DELETE FROM agent_entity_memory ; (d) cross-tenant : compte A trigger mutation entité B → RLS ne trouve pas → entity_memory inchangée + log warning ; (e) LLM down → log warning, retry next trigger, mutation business intacte.

### Implementation for User Story 7

- [ ] T044 [P] [US7] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/memory/entity_memory.py` : `async def update_entity_memory(account_id, entity_type, entity_id, db) -> None` (cf. contracts/entity-memory-update.md). LLM call avec prompt strict (factuel, sourcé, max 800 tokens). UPSERT version++. Audit log.
- [ ] T045 [US7] Enregistrer le hook post-mutation dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/app/agent/memory/__init__.py` (cf. contracts) : import dispatcher F55, register `_hook` qui enqueue BackgroundTask. Initialiser au boot via `app/main.py` startup event ou via import-time side effect (le module est déjà importé par F55 pour les tests).
- [ ] T046 [US7] Faire passer T043 (RED→GREEN).

**Checkpoint**: Entity memory opérationnelle. US1-US7 fonctionnels.

---

## Phase 10: User Story 8 — Cache embedding par tour (Priority: P2)

**Goal**: Embedding de la `user_message` du tour calculé une seule fois, partagé entre recall_memory auto et recall_history tool.

**Independent Test**: Tour avec recall auto + 1 tool recall_history sur même query → 1 seul appel Voyage embed (mock spy).

### Tests for User Story 8 (RED first)

- [ ] T047 [P] [US8] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_embedding_cache.py` : (a) recall auto compute embedding A, recall_history tool même query → 1 seul appel Voyage ; (b) recall_history tool query différente → 2 appels ; (c) cache scope = un tour : nouveau tour, même query → 1 nouveau appel ; (d) checkpointer F53 ne persiste PAS embedding_cache (verify exclude=True).

### Implementation for User Story 8

- [ ] T048 [US8] Vérifier que `embedding_cache.get_or_compute` (T016) est correctement appelé par BOTH `recall_memory` node ET `recall_history` handler — passe le même `state.embedding_cache` ref.
- [ ] T049 [US8] Faire passer T047 (RED→GREEN). Spy Voyage embed mock.

**Checkpoint**: Embedding cache opérationnel. US1-US8 fonctionnels.

---

## Phase 11: User Story 9 — Tracing des recalls (Priority: P2)

**Goal**: Chaque recall (auto ou tool) écrit une ligne `recall_log` avec agent_run_id, recall_type, query_hash, top_k, top_scores, latency_ms.

**Independent Test**: Tour avec recall auto + 1 tool → 2 lignes recall_log (auto+tool) avec agent_run_id partagé.

### Tests for User Story 9 (RED first)

- [ ] T050 [P] [US9] Écrire `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/integration/test_memory_recall_log.py` : (a) tour avec auto + tool → 2 entries recall_log avec même agent_run_id ; (b) entry contient query_hash (pas query brute) ; (c) top_scores JSONB list de `{message_id, score}` triée DESC ; (d) latency_ms > 0 ; (e) UPDATE/DELETE recall_log refusés au rôle applicatif (P3).

### Implementation for User Story 9

- [ ] T051 [US9] Vérifier que `recall_memory` node (T019) et `recall_history` handler (T023) appellent BOTH `recall_log.write_recall_log` (T018) avec les bons paramètres.
- [ ] T052 [US9] Faire passer T050 (RED→GREEN).

**Checkpoint**: Tracing opérationnel. US1-US9 fonctionnels.

---

## Phase 12: E2E Frontend Playwright (couvre US3 + US4)

**Goal**: 1 spec Playwright minimal qui appelle directement `GET` puis `DELETE /me/chat/threads/{id}/memory` via fetch direct (sans toucher MemoryBadge.vue ni F32 page).

- [ ] T053 [P] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/memory.spec.ts` : (a) auth PME via fixture, (b) seed thread avec 50 messages, (c) `GET /me/chat/threads/{id}/memory` → vérifier shape MemorySnapshotV2 dans la réponse JSON, (d) `DELETE /me/chat/threads/{id}/memory` → 200 idempotent, (e) re-GET → embeddings_purged=0, summary=null. Couvre SC-003 + SC-004 côté frontend.

---

## Phase 13: Polish & Cross-Cutting Concerns

- [ ] T054 [P] Documenter dans `/Users/mac/Documents/projets/2025/esg_mefali_v2/specs/057-agent-memory-rag/quickstart.md` (déjà créé) tout ajustement post-implémentation des paramètres HNSW (`m`, `ef_construction`, `ef_search`) si benchmark le suggère.
- [ ] T055 [P] Créer le golden set `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/llm_eval/golden_memory_recall.jsonl` avec ≥ 30 cas thread→query→message_id attendu (NFR-003), couvrant scénarios SC-001 + SC-005 + SC-008.
- [ ] T056 [P] Créer `/Users/mac/Documents/projets/2025/esg_mefali_v2/backend/tests/llm_eval/test_memory_recall_precision.py` : run le golden set et asserter ≥ 80 % top-3 précision (NFR-003 + SC-008).
- [ ] T057 Faire passer `make lint` (ruff sur `app/agent/memory/*` et `app/chat/memory/*` + `app/agent/nodes/recall_memory.py`).
- [ ] T058 Faire passer `make test` (pytest --cov + vitest run + Playwright). Vérifier coverage ≥ 90 % sur `app/agent/memory/*` et `app/agent/nodes/recall_memory.py`, ≥ 80 % global.
- [ ] T059 Mettre à jour `/Users/mac/Documents/projets/2025/esg_mefali_v2/CLAUDE.md` (markers SPECKIT START/END) : pointer vers `specs/057-agent-memory-rag/plan.md` (en remplaçant la valeur F56 si encore présente — résolu au merge orchestrateur).
- [ ] T060 Run quickstart.md scénario manuel sur env dev (cf. `quickstart.md` smoke test) : créer thread, 50 msgs, query recall, GET memory, DELETE memory. Vérifier comportement attendu.
- [ ] T061 Audit final P2/P3/P9 : cross-thread isolation tests, audit_log cohérence, Pydantic strict guard ; documenter le résultat dans une note `tests/integration/F57_AUDIT.md` (court, < 1 page) ou en commentaire de PR.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** : sans dépendance, peut démarrer immédiatement.
- **Foundational (Phase 2)** : dépend de Setup. **BLOQUE TOUTES les user stories.**
- **User Stories (Phase 3-11)** : dépendent de Foundational. Ordres :
  - US1 (P1, T015-T021) : indépendante des autres stories.
  - US2 (P1, T022-T025) : dépend de embedding_cache (T016) + long_term (T017) + recall_log (T018) de US1.
  - US3 (P1, T026-T029) : dépend uniquement de Foundational (schemas + entities_referenced helper T011).
  - US4 (P1, T030-T033) : dépend de service `forget_thread_memory` (T031) ; le test cross-tenant (T030.c) requiert que US3 expose la route GET sur le thread, donc finir US3 d'abord pour shared route file `chat/memory/api.py`.
  - US5 (P1, T034-T037) : dépend de US1+US2 (long_term + recall_history présents pour valider l'isolation).
  - US6 (P2, T038-T042) : dépend de Foundational + US1 (recall_memory doit consommer le summary).
  - US7 (P2, T043-T046) : dépend de Foundational + dispatcher F55 (mergé).
  - US8 (P2, T047-T049) : dépend de US1 (embedding_cache) + US2 (recall_history).
  - US9 (P2, T050-T052) : dépend de US1+US2 (recall_log écrits par les deux paths).
- **E2E (Phase 12)** : dépend de US3+US4.
- **Polish (Phase 13)** : dépend de toutes les user stories complètes.

### User Story Dependencies (résumé visuel)

```
Phase 2 Foundational (T006-T014)
    ├── US1 (T015-T021)  →  US2 (T022-T025)
    │      │
    │      └─→ US5 (T034-T037)  ←── US2
    │      └─→ US8 (T047-T049)  ←── US2
    │      └─→ US9 (T050-T052)  ←── US2
    │
    ├── US3 (T026-T029)
    │      │
    │      └─→ US4 (T030-T033)  (shared chat/memory/api.py)
    │
    ├── US6 (T038-T042)
    └── US7 (T043-T046)

Phase 12 E2E (T053) ← US3 + US4
Phase 13 Polish (T054-T061) ← all
```

### Within Each User Story

- Tests écrits AVANT implementation (RED), puis implementation (GREEN), puis refactor (IMPROVE).
- Models/Pydantic schemas avant services.
- Services avant endpoints.

### Parallel Opportunities

- T001-T005 (Setup) : tous [P], peuvent paralléliser.
- T006-T008 (foundational tests RED) : tous [P].
- T010, T013 (ORM models, AgentState extension) : [P] vs T009 (migration) qui doit être terminée pour T011/T012 (repository, schemas) qui touchent même fichier que F18.
- US1+US3 peuvent paralléliser après Foundational (US3 ne dépend pas de US1).
- US2 dépend de US1.
- US6 + US7 peuvent paralléliser entre eux et avec US3+US4 après Foundational.
- T015, T022, T026, T030, T034, T038, T043, T047, T050, T053 (tous les tests RED) : [P].
- T016, T017, T018 (US1 modules independents) : [P] entre eux.
- T039, T044 (US6 compactor + US7 entity_memory) : [P] (différents fichiers).
- T054, T055, T056 (Polish indépendants) : [P].

---

## Parallel Example: Foundational + Story 1

```bash
# Tasks parallèles avant migration (RED)
Task T006: "RLS test agent_entity_memory in test_memory_rls_entity_memory.py"
Task T007: "RLS test recall_log in test_memory_rls_recall_log.py"
Task T008: "Schema extensions test in test_memory_schema_extensions.py"

# Après T009 (migration) puis T010-T013 en //:
Task T010: "ORM AgentEntityMemory + RecallLog in app/agent/memory/models.py"
Task T013: "Extend AgentState with embedding_cache + recall_log_entries"

# Story 1 RED en // (après T014 GREEN foundational):
Task T015: "Test recall auto in test_memory_recall_auto.py"

# Implementations US1 en //:
Task T016: "EmbeddingCache module"
Task T017: "LongTerm cosine search module"
Task T018: "RecallLog writer module"
# T019 dépend de T016+T017+T018.
```

---

## Implementation Strategy

### MVP First (US1+US2+US3+US4 — toutes P1)

1. Compléter Phase 1: Setup (T001-T005).
2. Compléter Phase 2: Foundational (T006-T014) — CRITICAL.
3. Compléter Phase 3: US1 (T015-T021).
4. Compléter Phase 4: US2 (T022-T025).
5. Compléter Phase 5: US3 (T026-T029).
6. Compléter Phase 6: US4 (T030-T033).
7. Compléter Phase 7: US5 (T034-T037) — anti-fuite, P1.
8. **STOP & VALIDATE** : tester US1-US5 indépendamment. Le MVP F57 P1 est livrable.

### Incremental Delivery

1. Phases 1-2 → fondation prête.
2. + US1 → recall auto fonctionne.
3. + US2 → tool LLM-callable.
4. + US3 → snapshot enrichi.
5. + US4 → forget RGPD.
6. + US5 → anti-fuite vérifiée (P1 close).
7. + US6 → compaction async (P2).
8. + US7 → entity memory (P2).
9. + US8 → cache (P2).
10. + US9 → tracing (P2).
11. + Phase 12 → E2E.
12. + Phase 13 → Polish + golden eval ≥ 80 % (gate constitution P9).

### Parallel Team Strategy

Avec plusieurs développeurs après Phase 2 :

- Dev A : US1 → US2 → US5 (chemin recall)
- Dev B : US3 → US4 (chemin endpoints)
- Dev C : US6 → US7 (chemin async / entity)
- Dev D : Phase 12 E2E + Phase 13 polish

---

## Notes

- [P] tasks = different files, no incomplete dependencies.
- [Story] label maps task to specific user story for traceability.
- Each user story independently testable per Independent Test criteria.
- Verify tests fail (RED) before implementing (GREEN) ; refactor (IMPROVE) ; repeat.
- Coverage gate `fail_under = 80` doit rester GREEN à chaque commit (CI/local).
- F56 parallèle : NE PAS modifier `backend/app/agent/sourcing/*`, `app/agent/handlers/cite_source.py`, `app/sourcing/*`, `app/agent/nodes/validate_payload.py`. Conflit attendu sur `.specify/feature.json` et `CLAUDE.md` (résolu au merge orchestrateur).
- `tasks.md` mentionne migration `0036_f57_memory_rag.py` ; renumérotation possible si F56 prend 0036 ou si l'ordre de merge change le head Alembic.
