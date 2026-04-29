# Tasks: F25 — Matching Projet ↔ Offre

**Branch**: `025-matching-projet-offre` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Convention

- `[T###]` ID — `[P]` parallélisable — description.
- TDD : tests rouges → implémentation → vert → refactor.

## Phase A — Schemas + heuristiques

- [T001] [P] Créer `backend/app/matching/__init__.py`.
- [T002] [P] Créer `backend/app/matching/schemas.py` : `OfferMatch`, `CritereMatch`, `MatchDetail`, `ComparatorRow`.
- [T003] [P] Créer `backend/tests/unit/matching/test_heuristics.py` (RED).
- [T004] Implémenter `backend/app/matching/heuristics.py` : `eval_money_range`, `eval_geo`, `eval_thematique`, `eval_instruments`, `eval_critere_json`, `score_layer`.

## Phase B — Service matching

- [T005] Tests RED `backend/tests/unit/matching/test_service.py`.
- [T006] Implémenter `backend/app/matching/service.py` (`match`, `detail`, `comparator`).
- [T007] Verts T005.

## Phase C — Service candidature

- [T008] [P] Tests RED `backend/tests/unit/matching/test_candidature_service.py`.
- [T009] Implémenter `backend/app/matching/candidature_service.py` (snapshot dict + SHA-256, INSERT, `record_audit`).

## Phase D — Router FastAPI

- [T010] Tests RED `backend/tests/integration/matching/test_routes.py`.
- [T011] Implémenter `backend/app/matching/router.py` (4 endpoints).
- [T012] Modifier `backend/app/main.py` : `include_router`.

## Phase E — Validation

- [T013] `pytest backend/tests/unit/matching backend/tests/integration/matching --cov=app.matching`.
- [T014] `ruff check backend/app/matching backend/tests/unit/matching backend/tests/integration/matching`.
- [T015] Couverture ≥ 80%.
- [T016] Log manuel `.cc-runtime/logs/manual-tests-25.md`.
- [T017] Commit final.

## DEFERRED

- Frontend Nuxt pages.
- Cron alertes (US5).
- Tool LLM `find_offers` (US8).
- Filtres serveur (US6).
