# Plan — F20 Skills Back-Office CRUD

## Architecture cible

```
backend/app/skills/
├── anti_injection.py     # F20 — scan(text) -> list[Issue]
├── validation.py         # F20 — validate_skill_payload(payload, db)
└── evaluator.py          # F20 — run_eval(skill, db) -> EvalReport (stub MVP)

backend/app/admin/routes/
└── skills.py             # F20 — APIRouter /admin/skills/*

backend/app/main.py       # include skills router avant admin_crud_router

backend/tests/unit/skills/
├── test_anti_injection.py
├── test_validation.py
└── test_evaluator.py

backend/tests/integration/admin/
└── test_admin_skills.py  # CRUD + publish + eval + versioning end-to-end
```

## Pourquoi un router dédié vs generic CRUD

La table `skill` (F19) n'a pas les colonnes `logical_id`, `parent_id`, `published_by`,
`pending` requises par `app/admin/crud_router.py` et `publish.py`. Le versioning skill
est par `(name, version)` (UNIQUE F19). Donc router dédié plus simple et plus sûr.

## Endpoints

| Méthode | Path | Description |
|---|---|---|
| GET | `/admin/skills/` | Liste paginée, filtres `status`, `domain` |
| POST | `/admin/skills/` | Create draft |
| GET | `/admin/skills/{id}` | Read + ETag |
| PUT | `/admin/skills/{id}` | Update (draft in-place / published → new version) |
| POST | `/admin/skills/{id}/publish` | Publish (sources verified + gating) |
| POST | `/admin/skills/{id}/run-eval` | Run eval golden examples |
| GET | `/admin/skills/{id}/versions` | Historique par `name` |
| POST | `/admin/skills/_estimate-tokens` | Estimation tokens |

## Configuration ajoutée (`app/config.py`)

```
SKILL_EVAL_GATING_TOOL_MATCH_MIN: float = 0.8
SKILL_EVAL_GATING_PAYLOAD_VALID_MIN: float = 0.9
SKILL_GOLDEN_EXAMPLES_MIN: int = 5
```

## Anti-injection patterns initiaux

```
PATTERNS = [
    (r"ignore (?:all |the |any )?previous instructions", "ignore_previous"),
    (r"you are now\b", "role_takeover_en"),
    (r"tu es (?:désormais|maintenant)\b", "role_takeover_fr"),
    (r"</system>|<system>", "system_tag"),
    (r"^system\s*:", "system_prefix"),
    (r"sk-[A-Za-z0-9]{20,}", "openai_key_leak"),
    (r"ghp_[A-Za-z0-9]{20,}", "github_token_leak"),
]
```
Caractères de contrôle (`[\x00-\x08\x0B\x0C\x0E-\x1F]`) flaggés séparément.

## Eval runner MVP (stub déterministe)

```
matches = [e for e in examples if e.get("expected_tool") in skill.tool_whitelist]
valid  = [e for e in examples if isinstance(e.get("expected_payload"), dict) and e["expected_payload"]]
```
Branchement réel pipeline F14 reportable F35.

## Validation payload

1. `name`, `domain`, `prompt_expert` requis non vides.
2. `prompt_expert` ≤ `SKILL_PROMPT_MAX_TOKENS * 4` chars.
3. Anti-injection scan (sauf override).
4. `activation_rules` parse via `ActivationRules` (F19).
5. `tool_whitelist` ⊂ tools_registry (fallback liste blanche statique).
6. Sources existent + `verification_status='verified'`.
7. `golden_examples` ≥ 5 au publish.

## Versioning

- Édition `draft` : UPDATE in-place.
- Édition `published` : INSERT `(name, version=current+1, status='draft')` cloné, copie `skill_source`.

## TDD pipeline

1. `test_anti_injection` ;
2. `test_validation` ;
3. `test_evaluator` ;
4. `test_admin_skills` integration (gated `requires_db`) ;
5. `ruff check` propre ;
6. coverage ≥ 80% sur app/skills/ + app/admin/routes/skills.py.

## Risques

- Tool registry exact non exposé : fallback hardcodé MVP.
- Fixture sources `verified` requise pour tests publish.
- Anti-injection : patterns minimaux MVP, override documenté.
