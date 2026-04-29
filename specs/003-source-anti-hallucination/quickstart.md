# Quickstart — F03 Source & Anti-Hallucination

## Prérequis

- F01 mergée : Postgres dockerisé + pgvector + clients Voyage / OpenRouter.
- F02 mergée : auth, RLS, rôles SQL.
- `.env` : `VOYAGE_API_KEY`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `JWT_SECRET`.

## Démarrage local

```bash
# 1. Postgres
docker compose up -d postgres

# 2. Backend
cd backend
source .venv/bin/activate
alembic upgrade head           # applique 003_source_table_and_unsourced_log.py
pytest -q                      # unit + integration + middleware retry + RLS
uvicorn app.main:app --reload  # http://localhost:8000

# 3. Frontend
cd frontend
pnpm install
pnpm dev                       # http://localhost:3000
pnpm test                      # vitest SourceCite
```

## Vérifications fonctionnelles rapides

1. **FR-001 / US1.1** : `psql ... -c "INSERT INTO indicateur(name) VALUES ('x');"` → erreur NOT NULL `source_id`.
2. **FR-013 / US1.4** : créer une source en tant qu'admin A, tenter `verified` par admin A → erreur trigger.
3. **FR-005 / US2.1** : `curl -X POST localhost:8000/internal/llm-tools/cite_source -d '{"source_id":"<verified_uuid>"}'` → 200 + objet Source.
4. **FR-008 / US3.1** : POST sortie LLM simulée `"Le seuil GCF est de 50 tCO2e"` sans `tool_calls` → 422 + raison `heuristic_match_no_tool` + retry décrémenté.
5. **FR-009 / US4** : ouvrir `http://localhost:3000/demo/source-cite-demo` → cliquer le picto → bottom sheet liste 3 sources avec leurs badges.
6. **FR-010 / US5** : `python -m app.utils.sources_appendix '<id1>,<id1>,<id2>,<pending_id>'` → markdown 2 entrées (dédoublonnées, `pending` exclue).
7. **FR-011 / US6** : `curl -H "Authorization: Bearer <admin_jwt>" localhost:8000/admin/unsourced-claims?days=30` → liste agrégée RLS scoped.

## Performance smoke test

- Charger 5000 sources `verified` (script `scripts/seed_sources_demo.py`).
- `pytest tests/perf/test_search_source_p95.py` → assert p95 < 200ms (1000 appels).
- `pytest tests/perf/test_middleware_p95.py` → assert middleware ajoute < 50ms p95.

## Eval set anti-hallucination

```bash
python -m app.eval.run_anti_hallucination tests/eval/llm_anti_hallucination_set.json
# attendu : 20/20 — 100% des cas non sourcés rejetés
```
