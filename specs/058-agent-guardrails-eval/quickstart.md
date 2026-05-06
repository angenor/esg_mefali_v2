# Quickstart — F58 Agent Guardrails

## Pré-requis

- Backend `.venv` créé (`make setup` déjà exécuté pour F53–F57).
- Postgres dockerisé démarré (`make db-up`).
- Variables `.env` de F53–F57 valides (notamment `LLM_API_KEY`, `VOYAGE_API_KEY`, `JWT_SECRET`).
- F36 PR #41 mergée (migration 0036 appliquée).

## 1. Installation des dépendances Python ajoutées par F58

Aucune dépendance lourde. Une seule lib runtime :

```bash
cd backend && source .venv/bin/activate
pip install langdetect==1.0.9
```

`httpx` est déjà installé via FastAPI/Voyage. Pas d'ajout pour le webhook Slack.

Mise à jour `pyproject.toml` :

```toml
dependencies = [
  # ... existant
  "langdetect>=1.0.9,<2.0",
]
```

## 2. Migration alembic

```bash
cd backend && source .venv/bin/activate
alembic upgrade head
# Doit appliquer 0037_f58_guardrails.py
```

Vérification :

```bash
psql -h localhost -U esg_mefali -d esg_mefali -c "\d agent_tool_status"
psql -h localhost -U esg_mefali -d esg_mefali -c "\d account" | grep daily_
psql -h localhost -U esg_mefali -d esg_mefali -c "\d agent_run" | grep -E "injection|pii_masked|loop_detected|circuit_breaker_open|mode"
```

## 3. Variables d'env F58 (optionnelles)

Ajouter dans `.env` :

```ini
# Mode agent (langgraph par défaut)
LLM_AGENT_MODE=langgraph    # ou raw, ou minimal

# Webhook Slack ops (optionnel — no-op si absent)
OPS_SLACK_WEBHOOK_URL=

# Estimation USD/1K tokens (configurable)
LLM_PRICE_PER_1K_TOKENS_USD=0.004

# Eval gating threshold (configurable)
EVAL_AGENT_THRESHOLD=0.75
```

## 4. Lancement des tests F58

### Tests unitaires (rapide)

```bash
cd backend && source .venv/bin/activate
pytest tests/unit/agent/guardrails/ -v --cov=app.agent.guardrails --cov-report=term-missing --cov-fail-under=85
```

### Tests intégration

```bash
pytest tests/integration/admin/test_agent_tools_router.py tests/integration/admin/test_agent_metrics_consolidated.py tests/integration/agent/ -v
```

### Tests E2E

```bash
pytest tests/e2e/test_agent_e2e_guardrails.py tests/e2e/test_agent_e2e_kill_switch.py tests/e2e/test_agent_e2e_minimal_mode.py tests/e2e/test_agent_e2e_eval_smoke.py -v
```

### Tout F58 en un coup

```bash
pytest tests/unit/agent/guardrails/ tests/integration/agent/ tests/integration/admin/test_agent_*.py tests/e2e/test_agent_e2e_*.py -v --cov=app.agent.guardrails --cov-fail-under=85
```

## 5. Lancement des éval CI

### Mode mock (rapide, gratuit, sur chaque PR)

```bash
python scripts/eval_agent.py --mode mock --threshold 0.75 --report report_mock.json
# Doit retourner exit 0 et pass_rate >= 0.75
```

### Mode real (quotidien nocturne ou PR `eval-required`)

```bash
LLM_API_KEY="sk-or-..." LLM_BASE_URL="https://openrouter.ai/api/v1" \
  python scripts/eval_agent.py --mode real --threshold 0.75 --report report_real.json
```

### Jailbreak fuzzing

```bash
python scripts/eval_jailbreak.py --mode mock --report jailbreak_report.json
# Tolérance zéro : exit 1 si une seule violation détectée
```

## 6. Test manuel des endpoints admin

### Disable / list / enable un tool

```bash
# Login admin → ADMIN_TOKEN
ADMIN_TOKEN="..."

# Disable
curl -X POST http://localhost:8010/admin/agent/tools/generate_dossier/disable \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "test manuel"}'

# List
curl http://localhost:8010/admin/agent/tools \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Vérifier que generate_dossier apparaît avec enabled=false

# Enable
curl -X POST http://localhost:8010/admin/agent/tools/generate_dossier/enable \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Métriques consolidées

```bash
curl "http://localhost:8010/admin/agent/metrics?period=7d" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
# Doit retourner les 6 sections : runs, tools, sourcing, security, cost, memory
```

## 7. Test manuel circuit breaker

Mocker via fixture httpx-mock dans un test :

```python
def test_circuit_breaker_opens_after_3_errors(httpx_mock, llm_client):
    for _ in range(3):
        httpx_mock.add_response(status_code=503)
        try:
            llm_client.complete("test")
        except Exception:
            pass

    from app.agent.guardrails.circuit_breaker import LLM_CIRCUIT_BREAKER
    assert LLM_CIRCUIT_BREAKER.is_open("llm_openrouter") is True
```

## 8. Test manuel mode `minimal`

```bash
# Démarrer backend en mode minimal
LLM_AGENT_MODE=minimal uvicorn app.main:app --reload --port 8010

# Envoyer un message qui devrait déclencher une mutation
curl -X POST http://localhost:8010/agent/chat \
  -H "Authorization: Bearer $PME_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Crée un projet solaire"}'
# Vérifier : la réponse n'invoque pas create_project,
# explique poliment qu'on est en mode dégradé,
# et agent_run.mode = 'minimal' en DB
```

## 9. Frontend admin metrics page (P2)

```bash
cd frontend && pnpm dev --port 3001
# Visiter http://localhost:3001/admin/agent/metrics (login admin requis)
# Vérifier les 6 cards : runs, tools, sourcing, security, cost, memory
```

## 10. Checklist de validation finale

- [ ] `make test` global passe (couverture globale >= 80%, F58 >= 85%).
- [ ] `make lint` ruff propre sur `app/agent/guardrails/`.
- [ ] Migration `0037` appliquée sans erreur ; downgrade testé localement.
- [ ] `scripts/eval_agent.py --mode mock` exit 0.
- [ ] `scripts/eval_jailbreak.py --mode mock` exit 0.
- [ ] Au moins 50 cas dans `agent_e2e.jsonl` ; au moins 100 prompts dans `jailbreak_prompts.jsonl`.
- [ ] Tests E2E F58 (4 fichiers) tous verts.
- [ ] Endpoints admin manuellement testés (curl).
- [ ] Doc inline (docstrings) sur tous les modules guardrails.
