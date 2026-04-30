# Tasks: F35 — Eval LLM Continue

**Branch**: `035-eval-llm-postprocess`
**Spec**: [spec.md](./spec.md) — **Plan**: [plan.md](./plan.md)

TDD strict. Couverture cible ≥ 80 %.

## US1 — Golden set + runner (P1)

- [ ] **T001** Créer `backend/tests/llm_eval/golden_seed.yaml` avec 10 cas seed.
- [ ] **T002** Tests `backend/tests/eval/test_golden_loader.py` (charge OK, schéma, malformé → ValueError).
- [ ] **T003** Implém `backend/app/eval/golden_loader.py` : `GoldenCase` (`@dataclass(frozen=True)`) + `load_cases(path, filter_tags?) -> list[GoldenCase]`.
- [ ] **T004** Tests `backend/tests/eval/test_compare_payload.py` (matrice : count_min/max, options_contain, equals, regex, payload vide).
- [ ] **T005** Implém `backend/app/eval/compare_payload.py` : `compare_payload(expected, actual) -> tuple[bool, str | None]`.
- [ ] **T006** Tests `backend/tests/eval/test_eval_runner.py` (fake LLMClient, passed/failed paths).
- [ ] **T007** Implém `backend/app/eval/eval_runner.py` : `run_eval(cases, llm_callable) -> EvalReport`.
- [ ] **T008** Tests `backend/tests/eval/test_report.py` (JSON + Markdown).
- [ ] **T009** Implém `backend/app/eval/report.py` : `to_json(report)`, `to_markdown(report)`.
- [ ] **T010** CLI `backend/app/scripts/run_llm_eval.py` : argparse `--filter`, `--output {json,markdown}`.

## US2 — Post-processeur (P1)

- [ ] **T011** Tests `backend/tests/eval/test_post_processor.py` :
  - énumération `1. … 2. … 3. …` → `chips_suggestion`
  - "préférez-vous A, B ou C ?" → `chips_suggestion`
  - chiffre/seuil sans `cite_source` → `unsourced_warning`
  - réponse avec `cite_source` → pas de signal
  - réponse vide / tool structuré → aucun signal.
- [ ] **T012** Patterns YAML `backend/app/llm/postprocess_patterns.yaml`.
- [ ] **T013** Implém `backend/app/llm/post_processor.py` : `load_patterns(path)`, `post_process(...)`.

## US3 — Endpoint admin (P1)

- [ ] **T014** Tests `backend/tests/eval/test_admin_llm_eval.py` :
  - 401 sans auth, 403 non-admin, 200 admin
  - filtre par `tags`, audit event `llm_eval.run`.
- [ ] **T015** Implém `backend/app/api/routes/admin_llm_eval.py` : `POST /api/admin/llm-eval/run` avec `Depends(get_current_admin)`.
- [ ] **T016** Wire-up `backend/app/main.py` : `app.include_router(admin_llm_eval_router)`.

## Polish

- [ ] **T017** Couverture ≥ 80 % : `pytest backend/tests/eval/ --cov=backend/app/eval --cov=backend/app/llm/post_processor --cov=backend/app/api/routes/admin_llm_eval`.
- [ ] **T018** Lint `ruff check`.
- [ ] **T019** Manual tests log → `.cc-runtime/logs/manual-tests-35.md`.

## Dépendances

- T002→T003 ; T004→T005 ; T006→T007 (req T003+T005) ; T008→T009 ; T010 req T003,T005,T007,T009.
- T011→T012→T013.
- T014→T015→T016 (T015 req T003,T005,T007).
- T017 final.
