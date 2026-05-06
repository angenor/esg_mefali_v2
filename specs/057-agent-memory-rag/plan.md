# Implementation Plan: Agent Memory & Long-term Recall (F57)

**Branch**: `057-agent-memory-rag` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/057-agent-memory-rag/spec.md`

## Summary

F57 enrichit le pipeline LangGraph (F53/F54/F55) avec une couche mémoire conversationnelle complète à 2 niveaux. Le nœud `recall_memory` (réécrit en remplacement du squelette F54) charge les 15 derniers messages chronologiques (court terme) et un top-K=3 de messages anciens via cosine search pgvector (long terme, seuil 0.7). Le tool `recall_history(query, limit)` exposé via le dispatcher F55 (catégorie READ) permet au LLM de chercher explicitement dans le thread courant. Une compaction async par chunks fixes de 50 messages (déclenchée à 100, 150, 200…) génère un résumé `chat_thread.summary` ≤ 500 tokens via LLM. Une nouvelle table `agent_entity_memory` (partagée par account) stocke les faits stables agent connaît sur chaque entité business, alimentée par hook post-mutation du dispatcher F55. Une table `recall_log` (RLS account_id) trace tous les recalls. L'endpoint `GET/DELETE /me/chat/threads/{id}/memory` est étendu (US3) et un forget RGPD synchrone purge embeddings + summary sans toucher aux messages bruts (P3) ni à `agent_entity_memory` (account-wide). Anti-fuite cross-thread garantie par RLS + scope `thread_id`.

## Technical Context

**Language/Version** : Python 3.12 (backend `.venv`), Node 20+ (frontend `pnpm`)
**Primary Dependencies** : FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 strict, LangGraph, langchain-core, pgvector ≥ 0.5 (HNSW), Voyage AI SDK ou httpx direct (`voyage-3.5`, 1024 dim), OpenRouter (`minimax-m2.7`), Nuxt 4, Pinia, Tailwind v4, Playwright (E2E)
**Storage** : PostgreSQL avec extension pgvector ; RLS account_id systématique (P2). Seul service Docker en dev (image `pgvector/pgvector:pg16`).
**Testing** : pytest + pytest-asyncio + httpx (backend, ≥ 90 % couverture sur `app/agent/memory/*` et `app/agent/nodes/recall_memory.py`) ; vitest (frontend) ; Playwright (1 spec E2E minimale qui appelle les endpoints via fetch direct, sans toucher MemoryBadge/F32).
**Target Platform** : Linux server, hosting EU/Afrique de l'Ouest uniquement (P. Souveraineté constitution, PAS d'US).
**Project Type** : Web service (backend FastAPI + frontend Nuxt) ; pas de mobile ni desktop dans cette feature.
**Performance Goals** :
- `recall_memory` p95 < 300 ms sur thread 100 msgs avec 100 K msgs totaux indexés HNSW (m=16, ef_construction=64).
- Tour LLM avec recall p95 < 1 s côté agent (hors LLM streaming).
- Compaction async non bloquante pour user, écriture summary < 5 s p95.
- Précision recall ≥ 80 % sur golden set 30 cas.
**Constraints** :
- Forget RGPD synchrone (200 OK = effectivement fait).
- Anti-fuite cross-thread : zéro message d'un thread B dans le contexte d'un thread A.
- Voyage / pgvector down → fallback dégradé sans crash 500.
- Lock optimiste sur `chat_thread.last_compacted_at` pour éviter double-compaction.
- Audit log P3 : tout write mémoire (compact, entity_memory CRUD, forget) ⇒ ligne audit `source_of_change='memory_system'`.
**Scale/Scope** :
- Cible 1000 PME × 50 messages/jour ≈ 50 K embeddings/jour (cf. risque Voyage quota documenté dans la spec).
- Threads jusqu'à 200 messages MVP (compaction réduit la pression pgvector au-delà).
- 1 nouvelle migration Alembic (`0036_f57_memory_rag.py` — vise 0036 car F56 prendra probablement 0035 ; renumérotation triviale au merge si conflit).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F57 ne capture pas de données métier ESG/financières directement ; `agent_entity_memory.sources_used JSONB` conserve les `source_id` de mutations sourcées (référencement, pas duplication). Le tool `recall_history` ne produit pas d'assertion factuelle, il restitue des messages stockés. | ✅ |
| P2 | Multi-tenant RLS | Toutes les nouvelles tables (`agent_entity_memory`, `recall_log`) portent `account_id NOT NULL` + RLS policy `USING (account_id = current_setting('app.current_account_id')::uuid)`. Cross-tenant retourne 404. Anti-fuite cross-thread additionnelle (scope `thread_id`+`account_id` sur tous les recalls). | ✅ |
| P3 | Audit log append-only | Compaction summary, `agent_entity_memory` CRUD, forget RGPD écrivent une ligne `audit_log` avec `source_of_change='memory_system'`, `entity_type`, `field`, `old_value`, `new_value`, `tool_call_id`/`agent_run_id` si présents. Aucune mutation silencieuse. | ✅ |
| P4 | Versioning + snapshot candidatures | `agent_entity_memory.version` est un compteur d'écritures (logique referential : update incrémente version, le summary courant remplace le précédent). Aucune table de référentiel ESG modifiée. Aucune candidature touchée. | ✅ |
| P5 | Money typé | F57 ne manipule pas directement de montants. Forget RGPD ne touche jamais aux montants Money en DB business — frontière documentée dans la spec et dans `quickstart.md` (« forget mémoire ≠ purge entités business »). | ✅ |
| P6 | Pivot Indicateur unique | F57 ne crée pas de duplication ESG par axe E/S/G. `agent_entity_memory.entity_type='Indicateur'` reste possible (référence), pas de stockage de valeurs E/S/G. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | F57 n'introduit aucun rôle externe. `agent_entity_memory` est strictement scopée par account (PME) ou Admin. Aucun webhook vers fonds/banque. | ✅ |
| P8 | Édition manuelle + sync LLM | Tout fait dans `agent_entity_memory` est un cache reproductible : la DB business reste source de vérité. Une mutation manuelle d'un champ business invalide la mémoire LLM courante (même mécanisme que F55 EventBus) et déclenche refresh entity_memory via le hook post-mutation du dispatcher. Aucune valeur LLM-only en lecture seule créée. | ✅ |
| P9 | Tool-use LLM fiable | `recall_history` : nom verbal, schéma Pydantic strict (`model_config = ConfigDict(extra='forbid')`, `query: str` non vide ≤ 256 chars, `limit: int` 1-10), docstring « use when / don't use when », validation amont par `validate_payload` F14, exécution par dispatcher F55 (catégorie READ), max 2 retries sur erreur structurée. ≤ 10 tools concurrents (recall_history s'ajoute aux tools existants sans dépassement). | ✅ |
| P10 | UX bottom sheet | F57 n'introduit AUCUN composant interactif inline dans la bulle LLM. Le test E2E Playwright minimal appelle directement les endpoints via fetch, sans rendu UI. La page F32 « Mes données » et MemoryBadge.vue sont hors scope (livrés ailleurs). | ✅ |

**Verdict initial** : ✅ Toutes les gates passent (Phase 0 research peut commencer).

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter (interchangeable par env) ; embeddings Voyage `voyage-3.5` (1024 dim).
- Dev local : backend en `.venv`, Postgres seul service dockerisé, frontend en `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement.
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 dès le MVP.
- Langue : français par défaut.

## Project Structure

### Documentation (this feature)

```text
specs/057-agent-memory-rag/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── memory-endpoint.md          # GET/DELETE /me/chat/threads/{id}/memory
│   ├── recall-history-tool.md      # Tool schema (Pydantic) + dispatcher contract
│   ├── recall-memory-node.md       # Internal LangGraph node contract
│   └── entity-memory-update.md     # Hook post-mutation contract
├── checklists/
│   └── requirements.md  # From /speckit-specify
└── tasks.md             # Phase 2 output (NOT created by /speckit-plan)
```

### Source Code (repository root, modifications F57)

```text
backend/
├── app/
│   ├── agent/
│   │   ├── memory/                    # NEW (F57)
│   │   │   ├── __init__.py
│   │   │   ├── long_term.py           # cosine search pgvector + threshold
│   │   │   ├── compactors.py          # async compact_thread (chunks 50)
│   │   │   ├── entity_memory.py       # CRUD + summary update via LLM
│   │   │   ├── embedding_cache.py     # transient AgentState dict per turn
│   │   │   └── recall_log.py          # write recall_log lines
│   │   ├── nodes/
│   │   │   └── recall_memory.py       # REWRITE TOTAL (was F54 stub)
│   │   ├── handlers/
│   │   │   └── recall_history.py      # NEW (F57) tool LLM-callable READ
│   │   ├── state.py                   # MINIMAL ADD : embedding_cache field on AgentState
│   │   └── tool_factory.py            # MINIMAL ADD : register recall_history tool
│   ├── chat/
│   │   └── memory/
│   │       ├── service.py             # EXTEND : memory_snapshot() + forget()
│   │       ├── repository.py          # EXTEND : RLS-aware queries
│   │       ├── api.py                 # EXTEND : GET/DELETE /me/chat/threads/{id}/memory
│   │       └── schemas.py             # EXTEND : MemorySnapshotV2 (backwards-compat)
│   ├── embeddings_client.py           # VERIFY : ensure 1024 dim guard, exposed cache helper
│   ├── config.py                      # ADD env vars (FR-013)
│   └── main.py                        # NO CHANGE expected (F55 already wires dispatcher)
├── alembic/
│   └── versions/
│       └── 0036_f57_memory_rag.py     # NEW migration (target 0036, renumber if F56 took it)
└── tests/
    └── integration/
        ├── test_memory_recall_auto.py             # US1 (recall court+long)
        ├── test_memory_recall_history_tool.py     # US2 (tool LLM-callable)
        ├── test_memory_snapshot_endpoint.py       # US3 (GET enriched)
        ├── test_memory_forget_rgpd.py             # US4 (DELETE synchronous)
        ├── test_memory_cross_thread_isolation.py  # US5 (anti-fuite)
        ├── test_memory_compaction.py              # US6 (async + lock)
        ├── test_memory_entity_memory.py           # US7 (post-mutation hook + delete cleanup)
        ├── test_memory_embedding_cache.py         # US8 (single Voyage call per turn)
        └── test_memory_recall_log.py              # US9 (tracing)

frontend/
└── tests/
    └── e2e/
        └── memory.spec.ts             # NEW Playwright minimal (fetch direct GET/DELETE)
```

**Structure Decision** : Backend domain layout aligné sur convention ESG Mefali (domain-per-feature). Le module `app/agent/memory/` regroupe la logique mémoire spécifique au pipeline LangGraph (RAG, compaction, entity memory, embedding cache). Le module `app/chat/memory/` (existant F18) est étendu pour les endpoints HTTP `GET/DELETE /me/chat/threads/{id}/memory` et la query layer RLS-aware. La frontière : `app/agent/memory/*` est appelée par le pipeline LangGraph (nodes, handlers) ; `app/chat/memory/*` est appelée par les routes API directes côté utilisateur (snapshot, forget). La migration Alembic vise `0036` (F56 prendra `0035`) ; en cas de conflit le merge orchestrateur renumérotera.

## Phase 0 — Research (research.md)

Décisions à documenter (toutes résolues, aucune NEEDS CLARIFICATION) :

1. **pgvector HNSW vs IVFFlat** — choix : HNSW `(m=16, ef_construction=64)` ; rationale : 100 K msgs cible, latence < 300 ms, qualité recall meilleure qu'IVFFlat sur petite/moyenne échelle, recommandé par pgvector docs ≥ 0.5 ; alternative IVFFlat rejetée (nécessite training, lente sur insert).
2. **Voyage SDK vs httpx direct** — choix : étendre `embeddings_client.py` existant (httpx + retry exponentiel) ; rationale : le SDK officiel Python existe (`voyageai`) mais embeddings_client.py existant fait déjà le job ; alternative SDK rejetée pour éviter une dépendance supplémentaire si l'existant suffit.
3. **Compaction LLM model** — choix : `minimax-m2.7` via OpenRouter (`LLM_MODEL`), prompt système « Résume ces 50 messages PME-agent en ≤ 500 tokens, factuel, en français, sans assertion non sourcée ». Alternative : modèle dédié plus rapide rejetée (pas de gain mesurable, contraint stack).
4. **Lock optimiste compaction** — choix : `UPDATE chat_thread SET last_compacted_at=now() WHERE id=:id AND (last_compacted_at IS NULL OR last_compacted_at < now() - INTERVAL '1 minute') RETURNING ...` ; si pas de row retournée, abort compaction concurrente. Alternative : advisory lock pg_advisory_lock rejetée (plus complexe à libérer en cas d'exception).
5. **Embedding cache structure** — choix : `dict[str, list[float]]` (clé = SHA-256 hex de la query) sur `AgentState.embedding_cache: dict` (champ Pydantic transient, exclu du checkpointer F53). Alternative : Redis rejetée (over-engineering pour 1 tour).
6. **Storage entities_referenced** — choix : extraction au runtime depuis les `chat_message.metadata` JSONB (existant F18 stocke les `tool_call_id` et `entity_refs` JSONB) ; pas de table dédiée. Alternative : table `chat_thread_entity_ref` rejetée (drift à maintenir, pas de gain).
7. **Tool category de recall_history** — choix : READ (cohérent F55 décision Q4 : ré-injection en `ToolMessage` avec budget tokens configurable, pas de mutation, pas de bottom sheet).
8. **Recall_log retention strategy** — choix : pas de purge automatique MVP ; env var `LLM_AGENT_RECALL_LOG_RETENTION_DAYS=90` documente l'intention. Job de purge cron post-MVP (F58 ou ops).
9. **Update entity_memory schedule** — choix : enqueue via `BackgroundTasks` FastAPI dans le hook `dispatcher.post_mutation` ; `update_entity_memory()` consume les changements pertinents (last 5 messages mentionnant l'entité) + le state DB courant et reformule le summary via LLM. Alternative : Celery rejetée (pas de Celery dans la stack).
10. **Voyage 1024 dim guard** — choix : validation `assert len(embedding) == 1024` au boot (`config.py`) et après chaque appel embedding ; échec fast si mismatch.

## Phase 1 — Design (data-model.md, contracts/, quickstart.md)

### data-model.md (résumé pour le plan ; détail dans le fichier)

**Tables modifiées** :

- `chat_thread` : ADD `summary TEXT NULLABLE`, `last_compacted_at TIMESTAMP NULLABLE`. Pas de RLS change (existant F12).
- `chat_message` : ADD `compacted BOOL NOT NULL DEFAULT FALSE`. Pas de RLS change. L'embedding pgvector existant (1024) est ré-indexé HNSW.

**Tables nouvelles** :

- `agent_entity_memory(id UUID PK DEFAULT gen_random_uuid(), account_id UUID NOT NULL, entity_type TEXT NOT NULL, entity_id UUID NOT NULL, summary TEXT NOT NULL, sources_used JSONB DEFAULT '[]'::jsonb, last_updated_at TIMESTAMP NOT NULL DEFAULT now(), version INT NOT NULL DEFAULT 1)`. UNIQUE `(account_id, entity_type, entity_id)`. RLS `USING (account_id = current_setting('app.current_account_id')::uuid)`.
- `recall_log(id UUID PK DEFAULT gen_random_uuid(), agent_run_id UUID NULLABLE REFERENCES agent_run(id), account_id UUID NOT NULL, thread_id UUID NOT NULL REFERENCES chat_thread(id) ON DELETE CASCADE, recall_type TEXT NOT NULL CHECK (recall_type IN ('auto','tool')), query_hash TEXT NOT NULL, top_k INT NOT NULL, top_scores JSONB NOT NULL, latency_ms INT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT now())`. INDEX `(account_id, agent_run_id)`, `(account_id, thread_id, created_at DESC)`. RLS `USING (account_id = current_setting('app.current_account_id')::uuid)`.

**Index pgvector** : `CREATE INDEX chat_message_embedding_hnsw_idx ON chat_message USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);` Documenté dans `quickstart.md` (tuning).

### contracts/

- `memory-endpoint.md` : OpenAPI YAML pour `GET /me/chat/threads/{id}/memory` (réponse `MemorySnapshotV2`) et `DELETE /me/chat/threads/{id}/memory` (réponse 200 idempotent).
- `recall-history-tool.md` : schéma Pydantic strict `RecallHistoryArgs` (`query: str` 1-256 chars, `limit: int` 1-10, default 5) + docstring use when / don't use when + comportement dispatcher F55 (READ category, ré-injection ToolMessage avec budget tokens).
- `recall-memory-node.md` : contrat interne LangGraph (input `AgentState`, output `dict` avec `messages: list[BaseMessage]` enrichi + `recall_log_entries: list[RecallLogEntry]`).
- `entity-memory-update.md` : hook post-mutation du dispatcher F55, signature `async def update_entity_memory(account_id: UUID, entity_type: str, entity_id: UUID, db: AsyncSession) -> None`, idempotent.

### quickstart.md (résumé)

- Comment tester localement la chaîne F57 : `make db-up`, `cd backend && source .venv/bin/activate && alembic upgrade head`, `uvicorn app.main:app --reload --port 8010`, scenario script « create thread + 50 msgs + recall ».
- Tuning index HNSW : pourquoi `m=16, ef_construction=64`, comment le réindexer si dataset change.
- Frontière forget RGPD : ce qui est purgé (embeddings, summary, last_compacted_at), ce qui reste (chat_message.content, agent_entity_memory, mutations business).
- Variables d'env (FR-013) avec valeurs par défaut.
- Mode dégradé (Voyage/pgvector down) : comportement attendu.

### Agent context update

CLAUDE.md référence déjà `specs/052-notifications-settings-extension/plan.md` (cf. `<!-- SPECKIT START -->` markers). À l'issue de F57, le marker pointe vers `specs/057-agent-memory-rag/plan.md`.

## Phase 1 — Re-evaluation Constitution Check

Toutes les gates restent ✅ après design :
- P2 : `agent_entity_memory` et `recall_log` portent `account_id` + RLS confirmés en data-model.md.
- P3 : audit_log écrit dans compactors.py, entity_memory.py, et l'endpoint DELETE memory ; tests `test_memory_*.py` vérifient la présence des lignes audit.
- P9 : `recall_history` schema Pydantic strict avec `extra='forbid'` confirmé en contracts/recall-history-tool.md.

Aucune violation, pas d'entrée Complexity Tracking nécessaire.

## Complexity Tracking

> Aucune violation de la constitution. Section vide.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | | |

## Risks & mitigations

| Risque | Mitigation |
|--------|------------|
| Conflit migration Alembic 0035/0036 avec F56 | Plan vise 0036, renumérotation triviale en post-merge ; le head Alembic accepte le DAG |
| Voyage quota explose (1000 PME × 50 msg/jour ≈ 50K embeddings/jour) | Cache embedding par tour (FR-011), embeddings calculés UNIQUEMENT sur insert (background task F18 existant), pas à chaque tour |
| pgvector HNSW lent sur < 10K msgs | Build OK pour n'importe quelle taille ; `ef_construction=64` raisonnable ; doc tuning dans quickstart.md |
| Drift entity_memory (entité supprimée) | Hook post-mutation `delete_*` enqueue purge ciblée ; test `test_memory_entity_memory.py::test_delete_purges_memory` |
| Race compaction concurrente | Lock optimiste sur `last_compacted_at` (cf. research.md #4) ; test `test_memory_compaction.py::test_concurrent_compaction_single_winner` |
| Privacy entity_memory : free-form summary peut contenir du personnel sensible | Prompt système restrictif : « factuel, sourcé, max 800 tokens, pas d'anecdote » ; eval golden cas ESG sensibles |
| Forget RGPD pendant compaction en cours | DELETE acquiert le même lock optimiste avant purge ; si compaction tient le lock, DELETE attend ou refuse proprement (latence < 5 s) |
| Cross-thread leak via cache embedding | Cache scope = un tour seulement (transient AgentState) ; key = hash(query) ne suffit pas si même query dans threads différents → key inclura aussi `thread_id` pour défense en profondeur |

## Parallelism Note

F56 (sourcing enforcement) tourne en parallèle. Zones partagées critiques :
- `backend/app/main.py` : F57 ne modifie pas (le dispatcher F55 wire déjà tout).
- `backend/app/config.py` : F57 AJOUTE des env vars en bas de fichier ; ne modifie pas les vars existantes.
- `backend/pyproject.toml` : F57 ne devrait pas avoir besoin de nouvelles deps (httpx + pgvector + sqlalchemy déjà présents). Si Voyage SDK officiel est jugé nécessaire post-research, ajout en bas de `[project.dependencies]`.
- `backend/alembic/versions/` : F57 vise `0036_f57_memory_rag.py` ; F56 prendra probablement `0035`. Conflit improbable.
- `.specify/feature.json` : conflit attendu au merge (F56 vs F57), résolu manuellement par orchestrateur.

Zones strictement F56 que F57 ne touche PAS :
- `backend/app/agent/sourcing/*`
- `backend/app/agent/handlers/cite_source.py`
- `backend/app/sourcing/*`
- `backend/app/agent/nodes/validate_payload.py` (F56 enrichira ; F57 le consomme tel quel)

## Phase 2 reminder

`/speckit-tasks` produira `tasks.md` ordonné par dépendances :
1. Foundational (P0) : migration Alembic + tests RLS + module skeletons.
2. Core (P1) : recall_memory node + long_term + recall_history tool + endpoints memory + cross-thread isolation tests.
3. Async (P2) : compaction + entity_memory + embedding cache + recall_log + tracing tests + 1 E2E Playwright.
4. Polish : doc, quickstart, eval golden cases (≥ 30).

Les tâches devront expliciter quelles sont **TDD-first** (tests écrits avant implémentation, RED → GREEN → REFACTOR) conforme constitution P9 (eval gating) et règle .claude `tdd-workflow`.
