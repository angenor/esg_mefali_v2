# F20 — Manual tests log

## Statut automatisé

- Unit tests `tests/unit/skills/` : **74 tests verts** (38 nouveaux F20).
- Coverage `app/skills/` : **97.63 %** (≥ 80 %).
- Ruff `app/skills app/admin/routes/skills.py tests/` : propre.
- Routes enregistrées dans `app/main.py` : confirmé.
- Integration `tests/integration/admin/test_admin_skills.py` : 14 tests écrits, **non exécutés** — la base Postgres locale contient un schéma de projet différent (tables `users, documents, …` sans `account_user/source/skill`). Problème d'environnement DB, pas du code F20.

## Endpoints implémentés

| Méthode | Path |
|---|---|
| GET | `/admin/skills/` (filtres status/domain) |
| POST | `/admin/skills/` (validation save, anti-injection, override, audit) |
| GET | `/admin/skills/{id}` + ETag |
| PUT | `/admin/skills/{id}` (draft in-place / published → new version) |
| POST | `/admin/skills/{id}/publish` (sources verified + gating) |
| POST | `/admin/skills/{id}/run-eval` |
| GET | `/admin/skills/{id}/versions` |
| POST | `/admin/skills/_estimate-tokens` |

## Scénarios couverts dans les tests

- SC-001 publish full flow → `test_publish_full_flow_with_verified_source`
- SC-002 source pending bloquée → `test_save_rejects_pending_source`
- SC-003 injection détectée → `test_create_blocks_on_injection` + unit
- SC-004 gating fail puis bypass → `test_publish_blocked_by_eval_gating_then_skip`
- SC-005 versioning v2 draft, v1 published reste → `test_versioning_on_published_edit`

## TODO post-réparation DB locale

1. Reset DB et `alembic upgrade head`.
2. `pytest -q tests/integration/admin/test_admin_skills.py`.

## Frontend

`[DEFERRED]` — formulaire admin Vue hors scope MVP backend.
