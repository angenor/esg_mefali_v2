# Quickstart — F55 Agent Tool Dispatch & SSE Bridge

Date: 2026-05-06

Ce quickstart guide un dev qui clone la feature, démarre les services, et exécute les tests E2E F55.

## Pré-requis

- Python 3.12, Node 18+, pnpm, Docker.
- F53 (LangGraph core) mergée dans `main`.
- F39, F40, F41 (UI bottom sheet, viz, chat) opérationnelles côté frontend.

## Étapes

### 1) Cloner la branche et installer

```bash
git checkout 055-agent-tool-dispatch-sse
make setup           # backend .venv + frontend pnpm install
```

### 2) Migrations DB

```bash
make db-up           # postgres (pgvector)
make migrate         # alembic upgrade head — applique la migration F55
```

Vérifier les nouvelles colonnes :
```bash
psql -h localhost -U esg_mefali -d esg_mefali -c "\d+ audit_log"      # tool_call_id, agent_run_id
psql -h localhost -U esg_mefali -d esg_mefali -c "\d+ tool_call_log"  # idempotency_key, agent_run_id, dispatch_result_kind
```

### 3) Lancer backend + frontend (3 terminaux)

```bash
# T1
make db-up

# T2
make backend         # uvicorn :8010

# T3
make frontend        # nuxt :3001
```

### 4) Tester le flow end-to-end

#### 4.1 — ASK / bottom sheet

Ouvrir `http://localhost:3001/chat`, envoyer :
> Quelle forme juridique pour ma boulangerie ?

Vérifier :
- La bulle assistant ne contient AUCUN input.
- Une bottom sheet F39 s'ouvre avec les options.
- Cliquer une option → le tour suivant s'enchaîne.

#### 4.2 — SHOW / viz inline

Envoyer :
> Affiche mon score ESG en radar.

Vérifier :
- Un radar chart se rend INLINE dans la bulle assistant.
- Les valeurs sont sourcées (P1).

#### 4.3 — Mutation + sync EventBus

Envoyer :
> Mets à jour mon secteur, c'est de la boulangerie pâtisserie.

Vérifier (admin tab Profil → Entreprise ouvert) :
- La page Profil reflète `secteur=C10.71` sans rechargement.
- Une ligne `audit_log` existe avec `source_of_change='llm'`, `tool_call_id`, `agent_run_id`.
- `tool_call_log.status='ok'`.

#### 4.4 — Confirmation destructive

Envoyer :
> Supprime mon projet de panneaux solaires.

Vérifier :
- Une bottom sheet `ask_yes_no` s'ouvre avec récap clair.
- Cliquer « Non » → le projet reste intact, `tool_call_log.status='cancelled_by_user'`.
- Re-envoyer la même demande, cliquer « Oui » → le projet est supprimé, ligne audit créée.

#### 4.5 — Rate limit

Lancer un script qui invoque 31 fois `update_company_profile` en 60 s :
```bash
cd backend && source .venv/bin/activate
pytest tests/integration/test_dispatch_rate_limit_31.py -v
```

Vérifier : 30 succès + 1 `tool_call_log.status='rate_limited'` + SSE error frontend.

#### 4.6 — Idempotence (reconnexion SSE)

Lancer le test dédié :
```bash
pytest tests/integration/test_dispatch_idempotency_replay.py -v
```

Vérifier : un seul row business créé pour la même `idempotency_key`.

#### 4.7 — Mode dry_run admin

```bash
curl -X POST http://localhost:8010/api/chat/stream \
  -H "Authorization: Bearer <admin_token>" \
  -H "X-Agent-DryRun: true" \
  -d '{"message": "supprime ce projet"}'
```

Vérifier : le SSE event est `dry_run:mutation`, aucune ligne audit, aucun row business modifié, le frontend affiche un bandeau « simulation ».

### 5) Tests automatisés

```bash
# Backend
cd backend && source .venv/bin/activate
pytest tests/unit -v                    # tests unitaires (dispatcher, mutation_ctx, rate_limit, idempotency, sse)
pytest tests/integration -v             # tests d'intégration (9 scenarios)
pytest tests/e2e -v                     # E2E pytest+httpx ASGI
pytest --cov=app/agent --cov-report=term-missing  # ≥ 90% sur dispatcher/mutation_ctx/rate_limit

# Frontend
cd frontend && pnpm vitest run           # composables + stores
pnpm playwright test e2e/chat-bottom-sheet.spec.ts e2e/chat-mutation-sync.spec.ts
```

### 6) Validation finale

Checklist avant merge :
- [ ] Migration Alembic appliquée et réversible (`alembic downgrade -1` puis `upgrade head`).
- [ ] Tests unit + integration + E2E passent.
- [ ] Couverture backend `app/agent/dispatcher.py`, `app/agent/mutation_ctx.py`, `app/agent/rate_limit.py` ≥ 90 %.
- [ ] Couverture frontend `useChatStream`, `useChatToolBridge`, `stores/chat` ≥ 80 %.
- [ ] Boot fail-fast vérifié : un tool MUTATION sans handler ou un tool sans category fait crasher le backend.
- [ ] Constitution check : 10/10 ✅ (cf. plan.md).
- [ ] Aucun `console.log` ou `print` dans le code de prod (warning hook PostToolUse).
- [ ] Lint ruff + eslint propres.

## Dépendances avec F54 (parallèle)

F54 modifie potentiellement `app/main.py`, `app/config.py`, `pyproject.toml`. F55 :
- Ajoute des entrées (env vars `LLM_AGENT_RATE_LIMITS`, `LLM_AGENT_RATE_LIMIT_BACKEND`, `LLM_AGENT_READ_BUDGET_TOKENS`, `LLM_AGENT_DRY_RUN_HEADER`) dans `config.py` sans modifier les lignes existantes.
- Ajoute le router/startup_event dans `main.py` sans toucher les lignes existantes.
- N'ajoute aucune dépendance dans `pyproject.toml` (tous les packages utilisés viennent de F53 : LangGraph, Pydantic, SQLAlchemy, asyncio).

Ne pas toucher : `app/agent/nodes/build_context.py`, `app/agent/nodes/recall_memory.py`, `app/agent/context/*`, `app/entreprise/`, `app/projets/`, `app/candidatures/`, `app/scoring/` (F54 zone).
