# Phase 0 — Research (F57 Agent Memory & RAG)

All `NEEDS CLARIFICATION` markers from Technical Context have been resolved. Decisions below are final and feed Phase 1 design.

## R1 — Index pgvector : HNSW vs IVFFlat

**Decision** : HNSW avec `m=16, ef_construction=64`.

**Rationale** :
- pgvector ≥ 0.5 supporte HNSW nativement (cf. doc officielle pgvector).
- Cible 100 K messages, latence p95 < 300 ms : HNSW domine IVFFlat en latence query sur cette taille.
- HNSW ne nécessite pas de phase de training initiale (`vector_cosine_ops` direct).
- Paramètres `m=16` (default éprouvé) et `ef_construction=64` (compromis qualité/temps de build) cohérents avec recommandations pgvector pour datasets multi-tenant.

**Alternatives considérées** :
- IVFFlat : nécessite training (`CREATE INDEX ... WITH (lists = N)`) + latence dégradée si dataset croît sans réindexation. Rejeté.
- pas d'index (full scan) : OK pour < 10K msgs en dev, inacceptable en prod (NFR-001). Rejeté.

**Impact data-model** : migration Alembic crée l'index `chat_message_embedding_hnsw_idx`. Tuning documenté dans `quickstart.md`.

## R2 — Voyage SDK officiel vs httpx existant

**Decision** : Étendre le `embeddings_client.py` existant (httpx) ; pas de nouvelle dépendance.

**Rationale** :
- `backend/app/embeddings_client.py` existe déjà (livré F18) et fournit déjà `async def embed(text: str) -> list[float]` avec retry exponentiel.
- Ajouter le SDK officiel `voyageai` Python introduirait une dépendance redondante.
- F57 ajoute uniquement : (a) garde dimension 1024 au boot, (b) helper de cache mémoire pour `AgentState`, (c) helper batch pour la compaction (réutilise endpoint Voyage `/embeddings` avec liste de strings).

**Alternatives considérées** :
- SDK `voyageai` : ajoute deps + complexité testabilité (mocking SDK plus délicat que mocker httpx). Rejeté.
- Fournisseur alternatif (Cohere, OpenAI embeddings) : viole la constitution (Voyage `voyage-3.5` est imposé). Rejeté.

**Impact code** : `app/embeddings_client.py` reçoit 2 helpers ajoutés (pas de modification destructive).

## R3 — LLM model pour la compaction

**Decision** : `minimax-m2.7` via OpenRouter (variable `LLM_MODEL`), prompt système strict.

**Rationale** :
- Constitution impose `LLM_MODEL=minimax-m2.7` par défaut, interchangeable par env.
- La compaction n'a pas besoin d'un modèle plus spécialisé : 50 messages → résumé ≤ 500 tokens est dans les capacités de minimax.
- Prompt système (en français) : « Résume ces messages PME-agent en ≤ 500 tokens. Reste factuel, conserve les chiffres clés et les engagements pris. Ne produis aucune assertion ESG/financière non sourcée. Format : 5-10 bullet points. »
- Eval golden : 30 cas thread→summary attendus, vérifier que les questions du recall test continuent à être répondues correctement après compaction (NFR-003).

**Alternatives considérées** :
- Modèle dédié résumé (`mistral-small`, `gpt-3.5-turbo`) : violerait la stack imposée et complexifierait le routing. Rejeté.
- Algorithme heuristique non-LLM (TF-IDF top-N sentences) : qualité insuffisante pour résumé conversationnel. Rejeté.

**Impact code** : `app/agent/memory/compactors.py` réutilise `app.llm_client.get_chat_completion()` existant.

## R4 — Lock optimiste compaction

**Decision** : SQL UPDATE conditionnel + RETURNING.

**Rationale** :
```sql
UPDATE chat_thread
SET last_compacted_at = now()
WHERE id = :thread_id
  AND (last_compacted_at IS NULL OR last_compacted_at < now() - INTERVAL '1 minute')
RETURNING id;
```
Si 0 rows retournés, la compaction est déjà en cours ailleurs (lock pris < 1 min) ; abort propre.
Si 1 row retournée, le worker courant détient le lock pour ce thread.
Le timeout 1 min est conservateur (compaction NFR-002 < 5 s) mais évite les deadlocks si un worker crash sans relâcher.

**Alternatives considérées** :
- `pg_advisory_lock(thread_id)` : performant mais devient orphelin si la connexion meurt sans `pg_advisory_unlock`. Rejeté.
- Mutex applicatif (asyncio.Lock par thread_id) : ne marche pas en multi-worker uvicorn. Rejeté.
- Aucun lock (idempotent) : risque de double-summary, gaspillage LLM. Rejeté.

**Impact code** : `app/agent/memory/compactors.py::compact_thread()` exécute le UPDATE avant tout LLM call, abort si 0 rows.

## R5 — Embedding cache : structure et scope

**Decision** : `dict[str, list[float]]` transient sur `AgentState`, scope = un tour.

**Rationale** :
- Brief F57 explicite : « calcul unique par tour ». Un tour = un cycle d'exécution du graph LangGraph.
- `AgentState` (livré F53) accepte un champ Pydantic `embedding_cache: dict[str, list[float]] = Field(default_factory=dict, exclude=True)`. Le `exclude=True` empêche le checkpointer F53 de le persister.
- Clé : `f"{thread_id}:{sha256(query)}"` — défense en profondeur contre cross-thread leak (R10).
- Garbage collected à la fin du run LangGraph (Python ref count).

**Alternatives considérées** :
- Redis avec TTL 60 s : over-engineering, ajoute dépendance. Rejeté.
- Cache process-wide LRU : fuite mémoire potentielle, partagé entre tenants ⇒ violation P2 RLS. Rejeté.
- Pas de cache (compute à chaque appel) : double appel Voyage par tour si recall auto + tool. Rejeté (coût quota).

**Impact code** : `app/agent/state.py` reçoit le champ ; `app/agent/memory/embedding_cache.py` fournit `get_or_compute(state, thread_id, query) -> list[float]`.

## R6 — `entities_referenced` pour endpoint memory snapshot

**Decision** : Extraction au runtime depuis `chat_message.metadata` JSONB existant.

**Rationale** :
- F18 stocke déjà `chat_message.metadata` JSONB qui contient les `tool_call_id` et les `entity_refs` JSONB (référencement business : `[{type: 'Entreprise'|'Projet'|'Candidature', id, label}]`).
- Une simple agrégation SQL `SELECT DISTINCT jsonb_array_elements(metadata->'entity_refs') FROM chat_message WHERE thread_id = :id` retourne la liste.
- Cohérent P6 : pas de duplication via une table side, le pivot est `chat_message.metadata`.

**Alternatives considérées** :
- Table `chat_thread_entity_ref(thread_id, entity_type, entity_id)` mise à jour à chaque insert message : drift à maintenir, complexité supplémentaire. Rejeté.
- Calcul depuis `audit_log` (entries qui ont `chat_message.id` comme parent) : couplage trop fort + perf douteuse. Rejeté.

**Impact code** : `app/chat/memory/repository.py::get_entities_referenced(thread_id) -> list[EntityRef]`. Performance attendue OK (< 50 ms sur 200 msgs).

## R7 — Tool category de `recall_history`

**Decision** : READ.

**Rationale** :
- F55 décision Q4 : tool READ ré-injecte un JSON résumé/structuré tronqué à un budget tokens configurable en `ToolMessage` au tour suivant.
- `recall_history` n'est pas une mutation, pas un input utilisateur (ASK), pas une visualisation (SHOW). C'est de la lecture pure → READ.
- Budget tokens dédié env var `LLM_AGENT_RECALL_HISTORY_MAX_TOKENS` (default 800) — chaque message ré-injecté tronqué si nécessaire.

**Alternatives considérées** :
- Catégorie SHOW (visualisation) : non, le résultat n'est pas affiché à l'utilisateur, il est ré-injecté au LLM. Rejeté.
- Nouvelle catégorie MEMORY : sur-spécification, READ fait le job. Rejeté.

**Impact code** : `app/agent/tool_factory.py` enregistre `recall_history` avec `ToolCategory.READ`. Le dispatcher F55 sait déjà quoi faire.

## R8 — Recall_log retention

**Decision** : Pas de purge automatique MVP, env var documente l'intention (`LLM_AGENT_RECALL_LOG_RETENTION_DAYS=90`).

**Rationale** :
- Volume estimé : 1000 PME × 50 msg/jour × 1.5 recall/msg = 75K rows/jour. À 90 jours = 6.75M rows. Acceptable PostgreSQL avec index.
- Job de purge cron post-MVP (F58 ou ops) : `DELETE FROM recall_log WHERE created_at < now() - INTERVAL ':retention_days days'`.
- Documentation de l'intention dans la migration permet de l'activer plus tard sans changement de schéma.

**Alternatives considérées** :
- Cron immédiat dans F57 : ajoute scheduler dependency (pg_cron ou apscheduler), out-of-scope MVP. Rejeté.
- Pas d'env var : moins explicite, risque d'oubli. Rejeté.

**Impact code** : `app/config.py` reçoit `LLM_AGENT_RECALL_LOG_RETENTION_DAYS=90`. Aucune logique de purge implémentée dans F57.

## R9 — Update entity_memory schedule

**Decision** : `BackgroundTasks` FastAPI dans le hook `dispatcher.post_mutation` de F55.

**Rationale** :
- F55 expose un hook post-handler. F57 enregistre `update_entity_memory(account_id, entity_type, entity_id, db)` qui sera exécuté async après chaque mutation aboutie.
- `BackgroundTasks` FastAPI : exécution after-response, dans le même process, sans dépendance externe. Cohérent avec F55 qui l'utilise déjà pour `entity_updated` event.
- La fonction lit les 5 derniers messages mentionnant l'entité + le state DB courant + l'ancien summary, puis demande au LLM de produire le nouveau summary.

**Alternatives considérées** :
- Celery / Dramatiq : ajoute message broker + worker. Out-of-scope MVP. Rejeté.
- Sync inline : bloque la latence de la mutation (NFR-002 violé). Rejeté.

**Impact code** : `app/agent/dispatcher.py` (existant F55) reçoit l'enregistrement du hook (1 ligne dans `app/agent/memory/__init__.py` qui s'enregistre au boot).

## R10 — Voyage 1024 dim guard

**Decision** : Validation au boot (`config.py`) + assert post-call.

**Rationale** :
- Constitution impose `voyage-3.5` (1024 dim). Si l'utilisateur change `VOYAGE_MODEL` en `voyage-large-2` (1536 dim), l'app DOIT échouer fast.
- `config.py` valide `VOYAGE_EMBEDDING_DIM == 1024` au boot. Si mismatch, raise `ConfigurationError`.
- `embeddings_client.py::embed()` ajoute `assert len(vec) == 1024, f"Voyage returned {len(vec)} dims, expected 1024"` après chaque call.

**Alternatives considérées** :
- Pas de guard : crash plus tard côté pgvector avec message obscur. Rejeté.
- Guard runtime mais pas boot : crash uniquement au premier embed. Rejeté.

**Impact code** : `config.py` ajoute la validation ; `embeddings_client.py` ajoute l'assert.

## Synthèse

10 décisions documentées, 0 NEEDS CLARIFICATION restant. Phase 1 design peut commencer.
