# Tasks — F20 Skills Back-Office CRUD

## P1 (MVP backend)

- [x] T001 — `app/skills/anti_injection.py` : scan(text) -> list[Issue]
- [x] T002 — Tests unit `test_anti_injection.py`
- [x] T003 — `app/skills/validation.py` : validate_skill_payload
- [x] T004 — Tests unit `test_validation.py`
- [x] T005 — `app/skills/evaluator.py` : run_eval (stub MVP)
- [x] T006 — Tests unit `test_evaluator.py`
- [x] T007 — Config `app/config.py` : SKILL_EVAL_GATING_*, SKILL_GOLDEN_EXAMPLES_MIN
- [x] T008 — Router `app/admin/routes/skills.py` : list/get/create/update + ETag/If-Match
- [x] T009 — `POST /admin/skills/{id}/publish`
- [x] T010 — `POST /admin/skills/{id}/run-eval`
- [x] T011 — `GET /admin/skills/{id}/versions`
- [x] T012 — `POST /admin/skills/_estimate-tokens`
- [x] T013 — Mount router dans `app/main.py`
- [x] T014 — Tests integration `test_admin_skills.py` (requires_db)
- [x] T015 — `ruff check` propre
- [x] T016 — Coverage ≥ 80% F20

## P2 (DEFERRED)

- [ ] T017 — Frontend Vue admin form skills — DEFERRED
- [ ] T018 — Branchement pipeline F14 réel dans evaluator — F35
- [ ] T019 — Comparaison versions, suggestions LLM — post-MVP
