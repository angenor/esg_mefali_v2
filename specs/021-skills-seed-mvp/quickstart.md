# Quickstart — Seed Skills MVP (F21)

## Prerequis

- Backend venv active : `source backend/.venv/bin/activate`
- DB up : `docker compose up -d postgres`
- Migrations a jour : `cd backend && alembic upgrade head`

## Executer le seed

```bash
cd backend
python -m scripts.seed_skills
```

Sortie attendue (exemple) :

```
[skill_esg_diagnostic] action=created status=draft version=1
[skill_score_gcf] action=created status=draft version=1
[skill_dossier_gcf_via_boad] action=created status=draft version=1
... 8 shells ...
{"created":11,"updated":0,"skipped":0,"published":0,"draft":11,"golden_examples":15,"duration_ms":1234}
```

Note : sans sources `verified` en base de dev, les skills critiques restent en `draft` (warning loggue).

## Re-run idempotent

```bash
python -m scripts.seed_skills
```

Resultat : `{"created":0,"updated":0,"skipped":0,...}`.

## Tests

```bash
cd backend
pytest -q tests/unit/test_seed_helpers.py tests/integration/test_seed_skills_e2e.py \
  --cov=scripts/seed_skills --cov=app/skills/seed_helpers --cov-report=term-missing
```

Cible : >= 80 % couverture sur le code F21.

## Lint

```bash
cd backend && ruff check scripts/ app/skills/seed_helpers.py
```

## Verification post-seed (manuel)

```sql
SELECT name, status, version, array_length(tool_whitelist,1) AS n_tools,
       jsonb_array_length(golden_examples) AS n_examples
FROM skill ORDER BY name;
```
