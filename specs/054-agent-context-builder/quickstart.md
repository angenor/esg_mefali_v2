# Quickstart — F54 Agent Context Builder

**Branch**: `054-agent-context-builder`
**Audience**: dev exécutant les tests / validant la latence / inspectant un prompt.

## Prérequis

```bash
make db-up                                  # postgres + pgvector
cd backend && source .venv/bin/activate
pip install -e .                            # ré-installer si pyproject modifié (tiktoken ajouté)
make migrate                                # applique l'ALTER agent_run (system_prompt_hash, prompt_version)
```

## Tests unitaires F54

```bash
cd backend
source .venv/bin/activate

# Tous les tests F54
pytest tests/unit/agent/context/ -v

# Snapshot invariants (échec si template modifié sans bump PROMPT_VERSION)
pytest tests/unit/agent/context/test_invariants_snapshot.py -v

# 6 cas de troncature
pytest tests/unit/agent/context/test_truncation_strategy.py -v

# Multi-tenant isolation (NFR-003)
pytest tests/integration/agent/test_multi_tenant_isolation.py -v

# Coverage spécifique modules F54 (cible ≥ 90 %)
pytest tests/unit/agent/context/ tests/integration/agent/ \
  --cov=app.agent.prompts \
  --cov=app.agent.context \
  --cov=app.agent.prompt_builder \
  --cov-report=term-missing \
  --cov-fail-under=90
```

## Tests E2E (Playwright + identité)

```bash
# Backend up sur port 8010
make backend &

# Tests pytest E2E identité / jailbreak
cd backend
pytest tests/e2e/agent/ -v -m e2e

# Test Playwright frontend (multi-tenant via UI, lit le prompt via endpoint admin)
cd frontend
pnpm test:e2e tests/e2e/agent-context-isolation.spec.ts
```

## Tests de performance (NFR-001)

```bash
cd backend
pytest tests/perf/agent/test_build_context_latency.py -v -m perf

# Sortie attendue:
# - cold cache: < 250 ms p95
# - hot cache: < 50 ms p95
```

## Inspecter un prompt construit en local

```bash
# 1. Démarrer un thread / déclencher un tour côté frontend
# 2. Récupérer le run_id depuis les logs (cherche prompt_built event)
# 3. Appeler l'endpoint admin (token admin requis)

curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8010/admin/agent-runs/<run_id>/prompt

# Réponse:
# - status="success" → {hash only}
# - status="error" → {hash + prompt complet en clair}
```

## Bumper PROMPT_VERSION

Si une modification intentionnelle de `INVARIANTS_TEMPLATE` ou `IDENTITY_BLOCK` est nécessaire :

1. Éditer `backend/app/agent/prompts/invariants.py` (ou `identity.py`).
2. Bumper `PROMPT_VERSION` (ex. "2026.05" → "2026.06").
3. Régénérer le snapshot : `pytest tests/unit/agent/context/test_invariants_snapshot.py --snapshot-update` OU mettre à jour manuellement `tests/unit/agent/context/snapshots/invariants_<version>.txt`.
4. Documenter le changement dans le commit ("feat(F54): bump PROMPT_VERSION 2026.06 — added new safety rule X").

## Variables d'environnement

```bash
# .env (root)
LLM_AGENT_PROMPT_BUDGET_TOKENS=4000     # NFR-002
LLM_TIKTOKEN_ENCODING=cl100k_base       # FR-005
```

## Logs structurés émis

```json
{
  "event": "prompt_built",
  "account_id": "5b9f…",
  "page": "/scoring/abc",
  "tokens_total": 3120,
  "parts_truncated": [],
  "duration_ms": 145,
  "cache_hit_business_ctx": true
}
```

```json
{
  "event": "prompt_budget_exceeded",
  "account_id": "5b9f…",
  "tokens_before": 5200,
  "tokens_after": 3850,
  "budget": 4000,
  "steps_applied": ["step1_indicateurs", "step2_projets_archived"]
}
```

## Validation rapide acceptance scenarios

| SC | Comment vérifier |
|---|---|
| SC-001 | Créer PME complète + 2 projets + 5 indicateurs → call build_system_prompt → grep secteur/score/projets dans la sortie. |
| SC-002 | Créer PME sans projet → call → vérifier "Aucun projet enregistré." |
| SC-003 | E2E : 2 comptes → tour A → grep noms B → 0 résultat. |
| SC-005/006 | pytest test_truncation_strategy.py (cas 50 et 200 indicateurs). |
| SC-008 | pytest test_invariants_snapshot.py — modifier le template → test échoue. |
| SC-009/010 | pytest tests/e2e/agent/test_identity_resilience.py + test_jailbreak_resilience.py |
| SC-011 | pytest tests/perf/agent/ -m perf |
| SC-012 | pytest --cov-fail-under=90 |
| SC-014 | pytest test_admin_prompt_endpoint.py (cas success vs error) |
