# Plan — F19 Skills Engine Loader

## Architecture cible

```
backend/app/skills/
├── __init__.py
├── activation_rules.py   # Pydantic ActivationRules + matching
├── loader.py             # load_active_skills(context, session)
├── fusion.py             # build_prompt(...)
├── sources.py            # resolve_sources(...)
├── snapshot.py           # snapshot_skill_version(...) interface
└── priority.py           # ordre dossier > scoring > diagnostic > générale

backend/app/models/skill.py       # Skill + SkillSource ORM
backend/app/api/internal_skills.py # endpoint /internal/skill-loader/test (dev only)

backend/alembic/versions/0014_f19_skill.py

backend/tests/unit/skills/
├── test_activation_rules.py
├── test_loader.py
├── test_fusion.py
├── test_sources.py
└── test_priority.py
```

## Schéma DB (alembic 0014)

```sql
CREATE TYPE skill_status AS ENUM ('draft','published');

CREATE TABLE skill (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  domain TEXT NOT NULL,
  prompt_expert TEXT NOT NULL,
  procedure TEXT NOT NULL DEFAULT '',
  tool_whitelist TEXT[] NOT NULL DEFAULT '{}',
  activation_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
  golden_examples JSONB NOT NULL DEFAULT '[]'::jsonb,
  status skill_status NOT NULL DEFAULT 'draft',
  created_by UUID REFERENCES account_user(id),
  verified_by UUID REFERENCES account_user(id),
  valid_from TIMESTAMPTZ,
  valid_to TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (name, version)
);

CREATE TABLE skill_source (
  skill_id UUID NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
  source_id UUID NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
  PRIMARY KEY (skill_id, source_id)
);

CREATE INDEX idx_skill_status ON skill(status);
CREATE INDEX idx_skill_domain ON skill(domain);
```

## TDD pipeline

1. test activation_rules → impl ;
2. test priority → impl ;
3. test fusion (fixtures sans DB) → impl ;
4. test sources (avec session mock) → impl ;
5. test loader (gated requires_db) → impl ;
6. test snapshot interface → impl ;
7. test endpoint internal (httpx) ;
8. coverage check ≥ 80 % sur `app/skills/`.

## Risques

- DB indisponible en CI → tests loader gated par `requires_db`.
- Glob page matching → `fnmatch` standard.
- ENUM PG : nouveau type `skill_status`, créé via alembic.
