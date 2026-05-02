# F35 — Manual Tests Log

Date: 2026-04-29
Branche: 035-eval-llm-postprocess

## CLI (US1, US3)

```bash
cd backend && source .venv/bin/activate
python -m app.scripts.run_llm_eval --output=markdown
```

Sortie observée:
- Total: 10
- Passed: 10
- Failed: 0
- tool_match_rate: 1.0
- payload_partial_match_rate: 1.0
- fallback_rate: 0.2

```bash
python -m app.scripts.run_llm_eval --filter=forme_juridique --output=json
```
→ rapport JSON déterministe, 1 cas filtré, status passed.

## Tests automatisés

```bash
python -m pytest tests/eval/ -q
# 55 passed
```

Couverture sur modules F35:
- app/eval/compare_payload.py: 100%
- app/eval/eval_runner.py: 100%
- app/eval/golden_loader.py: 100%
- app/eval/report.py: 100%
- app/llm/post_processor.py: 98%
- TOTAL: 99.32%

```bash
python -m pytest tests/integration/admin/test_llm_eval_routes.py -q
# 7 skipped (schema absent dans cet env, fixture _schema_ready guard)
```

## Lint

```bash
python -m ruff check app/eval app/llm/post_processor.py app/api/routes/admin_llm_eval.py app/scripts/run_llm_eval.py tests/eval tests/integration/admin/test_llm_eval_routes.py
# All checks passed!
```

## Run 2026-05-02 — agent

- [x] CLI `python -m app.scripts.run_llm_eval --output=markdown` → 10 passed / 0 failed, fallback_rate=0.2, tool_match_rate=1.0.
- [x] CLI `--filter=forme_juridique --output=json` → 1 cas filtré, status passed, JSON déterministe.
- [x] `POST /api/admin/llm-eval/run` avec compte PME → **403** `{code:"forbidden"}` (RBAC OK).

Aucun fix nécessaire pour F35.

## Notes

- Endpoint POST /api/admin/llm-eval/run: enregistré dans app.main, routes loaded:186.
- Stub LLM déterministe en MVP : tous les cas non-fallback passent, fallback_rate calculé sur les 2 cas avec expected.tool="__fallback__".
- Schéma DB absent dans cet env → tests d'intégration auto-skip via _schema_ready().
- Aucune régression observée sur tests/eval + tests/orchestrator (153 passed).
- Failures pré-existantes sur tests/unit/test_migration_smoke* et tests/unit/skills/test_validation* → confirmées présentes AVANT cette feature (vérifié via git stash).
