# Quickstart — F53 Agent LangGraph Core

**Branch** : `053-agent-langgraph-core`
**Audience** : dev backend qui implémente la feature ; agent E2E qui rejoue les tests.

## Prérequis

- Postgres dockerisé up (`make db-up`)
- `.venv` backend installé (`cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -e .`)
- Migrations existantes appliquées (`make migrate`)
- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` configurés dans `backend/.env`
- (Optionnel) `VOYAGE_API_KEY` pour les embeddings F18

## 1. Activer l'agent (mode `langgraph`)

```bash
# backend/.env
LLM_AGENT_MODE=langgraph             # défaut
LLM_AGENT_MAX_TOOLS=10
LLM_AGENT_MAX_RETRIES=2
LLM_AGENT_TIMEOUT_S=30.0
LLM_AGENT_TRACE=db                   # ou db+stdout pour debug
```

Démarrer le backend :

```bash
make backend
# OU
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8010
```

Le backend journalise au boot :
```
[agent] compiling graph...
[agent] setting up postgres checkpointer (idempotent)...
[agent] graph compiled in 1842 ms, ready.
```

Vérifier le healthcheck :

```bash
curl -s http://localhost:8010/health/agent | jq .
# → { "ok": true, "langgraph_compiled": true, "postgres_checkpointer": true, "llm_reachable": true, "mode": "langgraph" }
```

## 2. Bascule rollback (mode `raw`)

```bash
# backend/.env
LLM_AGENT_MODE=raw
```

Redémarrer le backend (ou reload uvicorn). Le healthcheck devient :

```bash
curl -s http://localhost:8010/health/agent | jq .
# → { "ok": true, "langgraph_compiled": false, "postgres_checkpointer": false, "llm_reachable": true, "mode": "raw" }
```

`POST /messages` bascule sur l'ancien `stream_assistant()` (proxy LLM brut, sans tools).

## 3. Tester l'agent (E2E backend pytest)

```bash
cd backend && source .venv/bin/activate

# Suite complète agent
pytest tests/ -k "agent" -v --cov=app/agent --cov-report=term-missing

# Tests E2E uniquement
pytest tests/e2e/ -v

# Test ciblé : création de projet via tool calls
pytest tests/e2e/test_agent_e2e_create_project.py -v

# Test ciblé : analyse ESG sourcée
pytest tests/e2e/test_agent_e2e_analysis_sourced.py -v

# Test isolation cross-tenant
pytest tests/integration/test_agent_cross_tenant.py -v

# Test cancellation
pytest tests/integration/test_agent_cancellation.py -v
```

Coverage target : ≥ 85 % sur `backend/app/agent/`. La commande affiche le pourcentage et liste les lignes manquantes.

## 4. Tester l'UI complète (Playwright)

```bash
cd frontend
pnpm exec playwright install chromium  # première fois
pnpm exec playwright test tests/e2e/agent-chat-create-project.spec.ts --headed
pnpm exec playwright test tests/e2e/agent-chat-cancellation.spec.ts --headed
```

Prérequis :
- Backend up sur 8010
- Frontend up sur 3001 (`pnpm dev` dans `frontend/`)
- Compte de test PME seedé (cf. `backend/tests/seed_test_account.py`)

Les specs Playwright valident :
- Chaîne UI complète : envoi message → bottom sheet → validation → projet visible (sans reload)
- Bouton « Stop » en plein streaming → SSE se ferme proprement, pas de message orphelin

## 5. Inspecter les traces

```sql
-- Liste des runs récents (dans psql ou Adminer)
SET app.current_account_id = '<your-account-uuid>';

SELECT id, started_at, completed_at, status, total_latency_ms, retry_count, final_node
FROM agent_run
ORDER BY started_at DESC LIMIT 20;

-- Steps d'un run particulier
SELECT node_name, latency_ms, tokens_in, tokens_out, tool_calls_count, status
FROM agent_run_step
WHERE run_id = '<run-uuid>'
ORDER BY started_at;
```

## 6. Tester les modes (CI parallèle SC-008)

```bash
# Job 1 — mode langgraph
LLM_AGENT_MODE=langgraph pytest tests/integration/test_agent_modes.py::test_langgraph_mode -v

# Job 2 — mode raw
LLM_AGENT_MODE=raw pytest tests/integration/test_agent_modes.py::test_raw_mode -v
```

Les deux MUST passer avant chaque release. Le runner CI doit donc lancer 2 jobs distincts (matrice).

## 7. Diagnostiquer une panne

| Symptôme | Cause probable | Action |
|----------|---------------|--------|
| `/health/agent` ok=false, llm_reachable=false | OpenRouter down ou clé invalide | Vérifier `LLM_API_KEY`, `LLM_BASE_URL` ; tester `curl $LLM_BASE_URL/models` |
| `/health/agent` 503 langgraph_compiled=false | Pin de version langgraph cassé | Vérifier `pip list | grep langgraph` ; revoir `pyproject.toml` |
| Réponse trop lente (> 30s) | LLM lent ou tool DB long | Inspecter `agent_run_step` pour identifier le nœud qui dépasse |
| Retries en boucle | Schéma d'un tool divergent du LLM | Inspecter `tool_call_log` ; revoir use_when du tool |
| Cross-tenant 404 attendu mais 500 obtenu | RLS pas appliqué (session sans `app.current_account_id`) | Vérifier middleware `AuthSessionMiddleware` |

## 8. Mocker le LLM en dev local

Pour développer sans clé OpenRouter active, utiliser la fixture `fakellm` dans les tests, OU pointer `LLM_BASE_URL` vers un serveur local (ex. LM Studio, Ollama avec ollama-openai-proxy).

```bash
# .env dev
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=llama3.1:8b
```

⚠ Pour les **tests CI**, toujours utiliser la fixture `fakellm` — pas d'appel réseau.

## 9. Reset / debug propre

```bash
# Vider les traces agent (DEV ONLY, jamais en prod — viole append-only)
psql $DATABASE_URL -c "TRUNCATE agent_run_step CASCADE; TRUNCATE agent_run CASCADE;"

# Reset checkpoints LangGraph (DEV ONLY)
psql $DATABASE_URL -c "TRUNCATE checkpoints CASCADE; TRUNCATE checkpoint_blobs CASCADE; TRUNCATE checkpoint_writes CASCADE;"
```

## 10. Démarrage rapide pour l'agent E2E runner

```bash
# Une seule commande pour tout valider F53
make db-up
make migrate
cd backend && source .venv/bin/activate
pytest tests/ -k "agent" --cov=app/agent --cov-fail-under=85
cd ../frontend
pnpm dev &           # background
sleep 5
pnpm exec playwright test tests/e2e/agent-chat-create-project.spec.ts tests/e2e/agent-chat-cancellation.spec.ts
```

Si tout passe → F53 est prêt.
