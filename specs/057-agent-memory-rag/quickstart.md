# Quickstart — F57 Agent Memory & RAG

## Prérequis

- F53 / F54 / F55 mergés sur `main`
- Postgres avec extension `pgvector >= 0.5` (vérifier `SELECT * FROM pg_extension WHERE extname='vector';` retourne ≥ 0.5)
- Voyage AI key valide (`VOYAGE_API_KEY` dans `.env`)
- LLM clé valide (`LLM_API_KEY`, `LLM_MODEL=minimax-m2.7`, `LLM_BASE_URL=https://openrouter.ai/api/v1`)

## Bring-up local (3 terminaux)

```bash
# Terminal 1 — Postgres pgvector
make db-up
docker compose ps  # healthy attendu

# Terminal 2 — Backend FastAPI
make migrate                      # applique la migration 0036_f57_memory_rag
make backend                      # http://localhost:8010
curl http://localhost:8010/health  # {"status":"ok","db":"ok"}

# Terminal 3 — Frontend Nuxt (uniquement pour le test E2E Playwright)
make frontend                     # http://localhost:3001
```

## Variables d'env (FR-013)

Ajouter à `.env` :

```bash
# F57 memory & RAG tuning
LLM_AGENT_MEMORY_TOP_K=3
LLM_AGENT_MEMORY_THRESHOLD=0.7
LLM_AGENT_MEMORY_RECENT_COUNT=15
LLM_AGENT_COMPACT_THRESHOLD=100
LLM_AGENT_COMPACT_BATCH_SIZE=50
LLM_AGENT_COMPACT_MAX_TOKENS=500
LLM_AGENT_ENTITY_MEMORY_MAX_TOKENS=800
LLM_AGENT_RECALL_HISTORY_MAX_TOKENS=800
LLM_AGENT_RECALL_LOG_RETENTION_DAYS=90
```

Ne PAS modifier ces valeurs sans rouvrir un /speckit-clarify (impacte les NFRs).

## Vérifier l'index pgvector HNSW

```sql
\d+ chat_message
-- Devrait montrer : "chat_message_embedding_hnsw_idx" hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)

-- Tuning : pour augmenter la qualité query (au détriment de la latence) :
SET hnsw.ef_search = 80;  -- default 40
```

## Scénario de validation manuelle (smoke test)

```bash
# 1. Créer un thread + 50 messages mock via API
TOKEN=<jwt PME valide>
THREAD_ID=$(curl -sX POST http://localhost:8010/me/chat/threads -H "Authorization: Bearer $TOKEN" | jq -r .id)

# 2. Insérer 50 messages alternés (5 mentionnent "solaire 50 kWc" en début de thread)
for i in {1..50}; do
  CONTENT="Message numéro $i"
  [ $i -le 5 ] && CONTENT="Sur le projet solaire 50 kWc, j'envisage..."
  curl -sX POST "http://localhost:8010/me/chat/threads/$THREAD_ID/messages" \
       -H "Authorization: Bearer $TOKEN" \
       -d "{\"content\":\"$CONTENT\"}"
done

# 3. Vérifier le snapshot mémoire
curl -s "http://localhost:8010/me/chat/threads/$THREAD_ID/memory" -H "Authorization: Bearer $TOKEN" | jq

# 4. Envoyer une requête qui devrait déclencher recall_memory auto
curl -sX POST "http://localhost:8010/me/chat/threads/$THREAD_ID/messages" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"content":"Reprends ce qu'\''on disait sur le solaire 50 kWc"}'
# → la réponse SSE devrait inclure les souvenirs

# 5. Forget RGPD synchrone
curl -sX DELETE "http://localhost:8010/me/chat/threads/$THREAD_ID/memory" -H "Authorization: Bearer $TOKEN" | jq
# → 200 + embeddings_purged: 50 + summary_cleared: true
```

## Frontière forget RGPD (P5/P3)

| Effet de DELETE /me/chat/threads/{id}/memory | OUI | NON |
|---|---|---|
| Purge `chat_message.embedding` (NULL) | ✓ | |
| Purge `chat_thread.summary` | ✓ | |
| Purge `chat_thread.last_compacted_at` | ✓ | |
| Purge `chat_message.content` | | ✓ (P3 audit) |
| Purge `agent_entity_memory` | | ✓ (account-wide, Q3) |
| Purge `recall_log` | | ✓ (historique tracing) |
| Purge entités business (`entreprise`, `projets`, `candidatures`) | | ✓ (P5 frontière) |

> **Frontière RGPD documentée** : effacer la mémoire conversationnelle du thread NE supprime PAS les données business saisies dans la PME. Pour effacer ces dernières, l'utilisateur passe par "Mes données" (F32, livré ailleurs, post-MVP pour entity_memory).

## Mode dégradé (NFR-008)

| Panne | Comportement attendu |
|---|---|
| Voyage API down | recall long terme skipped, log warning ; les 15 derniers msgs court terme + summary continuent à être chargés ; tour LLM continue |
| pgvector down (extension manquante) | recall long terme skipped, idem |
| Compaction LLM call échoue | log warning, `last_compacted_at` non mis à jour, retry au prochain trigger |
| BackgroundTasks queue saturée | log warning, skip update_entity_memory ; mutation business intacte |
| Embedding dim mismatch (≠ 1024) | échec FAST au boot (`ConfigurationError`), backend ne démarre pas |

## Tests à exécuter

```bash
# Backend integration
cd backend && source .venv/bin/activate
pytest tests/integration/test_memory_*.py -v --cov=app/agent/memory --cov=app/agent/nodes/recall_memory --cov-report=term-missing

# Frontend E2E (Playwright minimal)
cd frontend
pnpm playwright test tests/e2e/memory.spec.ts
```

Coverage attendue : ≥ 90 % sur `app/agent/memory/*` et `app/agent/nodes/recall_memory.py`.

## Eval golden set (NFR-003)

Le golden set 30 cas thread→query→message attendu vit dans `backend/tests/llm_eval/golden_memory_recall.jsonl` (à créer). Chaque ligne :

```json
{"thread_seed": "fixture_solaire_50kwc.json", "query": "budget rénovation", "expected_message_id": "...", "rationale": "user a mentionné le budget 8M FCFA au msg 12"}
```

Run : `pytest tests/llm_eval/test_memory_recall_precision.py` ; gate à 80 % top-3.

## Tuning HNSW production

- m=16 / ef_construction=64 cibles 100K msgs / 1ms p50 / 50ms p99.
- Si dataset > 1M msgs : reconsidérer m=24, ef_construction=128 (recreate index).
- Si latence dégrade : `SET hnsw.ef_search = 80;` au début de la query (boost qualité).

## Points de vigilance

1. **Conflit migration Alembic** : F56 prend probablement `0035`, F57 vise `0036`. Si F57 mergeait en premier, ajuster `down_revision` au moment du second merge.
2. **Voyage quota** : 1000 PME × 50 msg/jour = 50K embeddings/jour. À monitorer.
3. **Race compaction** : lock optimiste UPDATE conditionnel sur `last_compacted_at` ; si mauvais comportement observé, examiner `recall_log` + `audit_log`.
4. **Anti-fuite cross-thread** : tous les selects DOIVENT inclure `WHERE thread_id = :id AND account_id = :guc`. Tests `test_memory_cross_thread_isolation.py` couvrent.
