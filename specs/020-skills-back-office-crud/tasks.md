# Tasks — F20 Skills Back-Office CRUD

## P1 (MVP backend)

- [ ] T001 — `app/skills/anti_injection.py` : scan(text) -> list[Issue]
- [ ] T002 — Tests unit `test_anti_injection.py`
- [ ] T003 — `app/skills/validation.py` : validate_skill_payload
- [ ] T004 — Tests unit `test_validation.py`
- [ ] T005 — `app/skills/evaluator.py` : run_eval (stub MVP)
- [ ] T006 — Tests unit `test_evaluator.py`
- [ ] T007 — Config `app/config.py` : SKILL_EVAL_GATING_*, SKILL_GOLDEN_EXAMPLES_MIN
- [ ] T008 — Router `app/admin/routes/skills.py` : list/get/create/update + ETag/If-Match
- [ ] T009 — `POST /admin/skills/{id}/publish`
- [ ] T010 — `POST /admin/skills/{id}/run-eval`
- [ ] T011 — `GET /admin/skills/{id}/versions`
- [ ] T012 — `POST /admin/skills/_estimate-tokens`
- [ ] T013 — Mount router dans `app/main.py`
- [ ] T014 — Tests integration `test_admin_skills.py` (requires_db)
- [ ] T015 — `ruff check` propre
- [ ] T016 — Coverage ≥ 80% F20

## P2 (DEFERRED)

- [ ] T017 — Frontend Vue admin form skills — DEFERRED
- [ ] T018 — Branchement pipeline F14 réel dans evaluator — F35
- [ ] T019 — Comparaison versions, suggestions LLM — post-MVP
