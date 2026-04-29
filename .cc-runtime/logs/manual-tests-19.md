# F19 — Manual tests log

Date: 2026-04-29
Branch: 019-skills-engine-loader

## Tests automatiques (TDD)

```
pytest -q tests/unit/skills/ --cov=app/skills --cov-report=term-missing
35 passed
Coverage app/skills : 97.76 %
```

## Lint

```
ruff check app/skills/ app/models/skill.py app/api/internal_skills.py \
  tests/unit/skills/ alembic/versions/0014_f19_skill.py
All checks passed!
```

## Couverture par module

| Module                          | Cover |
|---------------------------------|-------|
| app/skills/__init__.py          | 100%  |
| app/skills/activation_rules.py  | 96%   |
| app/skills/fusion.py            | 100%  |
| app/skills/loader.py            | 100%  |
| app/skills/priority.py          | 96%   |
| app/skills/snapshot.py          | 100%  |
| app/skills/sources.py           | 96%   |

## Endpoint à tester manuellement (post-migration)

```bash
# 1) appliquer la migration 0014_f19_skill
alembic upgrade head

# 2) seed une skill via SQL (en attendant F20/F21)
psql ... <<SQL
INSERT INTO skill (name, version, domain, prompt_expert, status, activation_rules)
VALUES ('skill_esg_diagnostic', 1, 'diagnostic', 'Tu es expert ESG.', 'published',
        '{"any_of":[{"page":"/profil/projets/*","intent":["analyse"]}]}');
SQL

# 3) tester
curl -X POST http://localhost:8000/internal/skill-loader/test \
  -H 'Content-Type: application/json' \
  -d '{"context":{"page":"/profil/projets/abc","intent":"analyse"}}'
```

## Régressions

Les échecs de `tests/unit/test_migration_smoke.py` sont **pré-existants**
(vérifiés via `git stash` avant les changements F19). Liés à un état Postgres
divergent des migrations, hors-scope F19.

## Scope livré

P1 livrés :
- T001 migration alembic 0014
- T002 ORM Skill + SkillSource
- T003 ActivationRules pydantic + matching
- T004 priority.py
- T005 sources.py resolve_sources
- T006 fusion.py build_prompt
- T007 loader.py load_active_skills
- T008 snapshot.py interface
- T009 endpoint POST /internal/skill-loader/test
- T010-T012 tests + 97.76 % coverage

Reportés (P2) :
- T013 persistence snapshot table thread_skill → F20
- T014 CRUD admin skill → F20
- T015 cache invalidation → post-MVP
