---
description: "Tasks list — F31 Plan d'Action ESG (MVP)"
---

# Tasks: F31 — Plan d'Action ESG (MVP)

**Input**: Design documents from `/specs/031-plan-action-rappels-bibliotheque/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, contracts/action-plan-api.yaml, quickstart.md

**Tests**: TDD strict requis (couverture ≥ 80 %).

**Organization**: tâches groupées par user story P1 (US1 + US2). Tout le reste de F31 est `[DEFERRED]`.

## Format

`- [ ] [TaskID] [P?] [Story?] Description with file path`

## Phase 1 — Setup

- [ ] T001 Créer le module `backend/app/action_plan/__init__.py` (squelette vide).
- [ ] T002 [P] Créer les dossiers de tests `backend/tests/unit/action_plan/`, `backend/tests/integration/action_plan/`, `backend/tests/contract/action_plan/` avec `__init__.py` chacun.

---

## Phase 2 — Foundational (Blocking Prerequisites)

**But** : tables, enums, modèles SQLAlchemy + migration Alembic + RLS. Sans cela aucune US n'avance.

- [ ] T003 Créer la migration Alembic `backend/alembic/versions/0021_f31_action_plan.py` :
  - création des 3 enums Postgres (`action_step_category`, `action_step_priority`, `action_step_status`),
  - création des tables `action_plan` et `action_step` (cf. data-model.md),
  - index `UNIQUE (account_id, version)` et `INDEX (plan_id, priority, horizon_at)`,
  - politiques RLS strictes selon research.md R-004,
  - downgrade complet.
- [ ] T004 [P] Modèle SQLAlchemy `backend/app/models/action_plan.py` (Mapped, types, FKs vers `account`, `score_calculation`, `account_user`).
- [ ] T005 [P] Modèle SQLAlchemy `backend/app/models/action_step.py` (Mapped, FKs vers `action_plan`, `account_user`, `indicateur`, `source`).
- [ ] T006 Importer les nouveaux modèles dans `backend/app/models/__init__.py` (cohérent avec le pattern existant).
- [ ] T007 [P] Enums Python `backend/app/action_plan/enums.py` (`Category`, `Priority`, `StepStatus`, `Horizon` — IntEnum 6/12/24).
- [ ] T008 [P] Schemas Pydantic v2 `backend/app/action_plan/schemas.py` :
  - `ActionStepRead`, `ActionStepPatch` (`extra='forbid'`, `min_properties=1`),
  - `ActionPlanRead`,
  - `Gap` (DTO interne pour le générateur),
  - aligné sur `contracts/action-plan-api.yaml`.

---

## Phase 3 — User Story 1 : Générer une feuille de route (P1)

**Goal** : `POST /me/action-plan/generate?horizon={6|12|24}` produit un plan versionné depuis le dernier `ScoreCalculation`.

**Independent test** : avec une PME ayant un `ScoreCalculation` injecté, l'appel renvoie 201 + plan persisté avec ≥ 1 étape priorisée. Sans score : 422.

### Tests d'abord (TDD RED)

- [ ] T009 [P] [US1] Tests unitaires `backend/tests/unit/action_plan/test_generator.py` :
  - mapping severity → priority (3 cas seuils : 0.20, 0.45, 0.70),
  - mapping horizon (haute/3, moyenne/2, basse/1),
  - mapping pillar → category (environnement+émission → carbone, autres → esg),
  - extraction `_extract_gaps` avec payload `details_json` synthétique (incl. cas vide → étape par défaut "Revue annuelle ESG"),
  - déterminisme : même input → même output.
- [ ] T010 [P] [US1] Tests unitaires `backend/tests/unit/action_plan/test_service.py` :
  - `generate` lève `NoScoreCalculationError` si aucun score,
  - `generate` produit version=1 puis version=2 sur 2nd appel,
  - chaque génération appelle `record_audit` (mock).
- [ ] T011 [P] [US1] Tests unitaires `backend/tests/unit/action_plan/test_schemas.py` :
  - `ActionStepPatch` rejette champs inconnus (`extra='forbid'`),
  - `ActionStepPatch` rejette `status` hors enum,
  - `ActionPlanRead` sérialise correctement (steps triées priorité desc, horizon_at asc).
- [ ] T012 [US1] Tests d'intégration `backend/tests/integration/action_plan/test_generate_endpoint.py` :
  - `POST /me/action-plan/generate?horizon=12` → 201 + body conforme,
  - `horizon=8` → 422,
  - sans `ScoreCalculation` → 422 avec message,
  - 2nd POST → version=2 et version=1 conservée.
- [ ] T013 [P] [US1] Test contract `backend/tests/contract/action_plan/test_openapi_contract.py` :
  - vérifie que `app.openapi()["paths"]` contient les 3 routes attendues avec opérations correctes.

### Implémentation (GREEN)

- [ ] T014 [US1] Implémenter `backend/app/action_plan/generator.py` :
  - `Gap` dataclass frozen,
  - `_extract_gaps(details_json) -> list[Gap]`,
  - `_severity_to_priority(score) -> Priority`,
  - `_priority_to_horizon_at(generated_at, horizon_months, priority) -> date`,
  - `_pillar_to_category(pillar, indicator_code) -> Category`,
  - `build_steps(gaps, generated_at, horizon_months) -> list[StepDraft]` (incl. fallback "Revue annuelle ESG").
- [ ] T015 [US1] Implémenter `backend/app/action_plan/service.py` :
  - `class NoScoreCalculationError(Exception)`,
  - `class ActionPlanService(session)`,
  - `_load_latest_score(account_id) -> ScoreCalculation | None`,
  - `_lock_and_next_version(account_id) -> int` (`SELECT MAX(version) FOR UPDATE`),
  - `generate(account_id, horizon_months, user_id) -> ActionPlan` (TX + audit),
  - `get_current(account_id) -> ActionPlan | None`,
  - `update_step(step_id, patch, user_id) -> ActionStep` (audit before/after).
- [ ] T016 [US1] Implémenter `backend/app/action_plan/routes.py` :
  - router FastAPI avec dépendances `get_current_user`, `require_role('pme')`, `get_db`,
  - `POST /me/action-plan/generate?horizon=...` → 201 / 422,
  - `GET /me/action-plan` → 200 / 404,
  - mappage exception `NoScoreCalculationError` → 422.
- [ ] T017 [US1] Wirer le router dans `backend/app/main.py` (`app.include_router(action_plan_router)`).

---

## Phase 4 — User Story 2 : Suivre/mettre à jour les étapes (P1)

**Goal** : `PATCH /me/action-plan/steps/{id}` permet d'éditer `status` et `responsible_user_id` avec audit.

**Independent test** : un PATCH valide change le statut, un GET ultérieur le reflète, et un audit log est inséré.

- [ ] T018 [US2] Tests d'intégration `backend/tests/integration/action_plan/test_patch_step_endpoint.py` :
  - PATCH `status=doing` → 200,
  - PATCH `status=blocked` → 422,
  - PATCH étape inconnue → 404,
  - PATCH responsible_user_id (uuid valide / null) → 200,
  - audit_log contient bien la mutation.
- [ ] T019 [US2] Tests d'intégration RLS `backend/tests/integration/action_plan/test_rls_isolation.py` :
  - PME B ne peut pas GET le plan de PME A (404),
  - PME B ne peut pas PATCH une étape de PME A (404),
  - PME B ne peut pas voir une `action_plan` row de PME A via SELECT direct quand RLS est en place.
- [ ] T020 [US2] Tests d'intégration `backend/tests/integration/action_plan/test_get_endpoint.py` :
  - GET sans plan → 404,
  - GET après generate → 200 + steps triées (priorité desc, horizon_at asc),
  - GET après 2 generate consécutifs → renvoie la version la plus récente.
- [ ] T021 [US2] Implémenter le endpoint `PATCH /me/action-plan/steps/{step_id}` dans `backend/app/action_plan/routes.py` (réutilise `service.update_step`).
- [ ] T022 [US2] Vérifier que `service.update_step` charge l'étape via JOIN avec `action_plan` (RLS impose le filtrage account_id automatiquement) et lève `HTTPException 404` si introuvable.

---

## Phase 5 — Polish & Cross-cutting

- [ ] T023 [P] Lancer `ruff check backend/app/action_plan backend/tests` et corriger.
- [ ] T024 [P] Lancer `mypy backend/app/action_plan` (si config présente) et corriger.
- [ ] T025 Vérifier la couverture : `pytest --cov=app/action_plan --cov-report=term-missing` → ≥ 80 %.
- [ ] T026 Compléter `.cc-runtime/logs/manual-tests-31.md` (suivi des tests manuels d'après quickstart.md).
- [ ] T027 [P] Sanity check : `alembic upgrade head` puis `alembic downgrade -1` puis `alembic upgrade head` doit fonctionner sans erreur.
- [ ] T028 Smoke check global : `pytest backend/tests` (toute la suite) — pas de régression sur F01..F30.

---

## [DEFERRED] — explicitement hors-scope MVP

> Ces items sont documentés mais NON exécutés dans cette feature. Reportés à des features ultérieures.

- [DEFERRED-1] Cron `notify_offer_deadlines`, `notify_inactive_candidatures`, `monthly_progress_digest` (FR-006 brouillon).
- [DEFERRED-2] Table `notification` + service email transactionnel (FR-007/008 brouillon).
- [DEFERRED-3] Tables `ressource` + sous-types (guides, templates, vidéos, FAQ) + endpoints CRUD admin (FR-009/010).
- [DEFERRED-4] Fiches intermédiaires (BOAD, PNUD, AFD, Ecobank) (FR-011 brouillon).
- [DEFERRED-5] Frontend Vue `/profil/plan-action` et `/ressources` (FR-005, FR-010).
- [DEFERRED-6] Tool LLM `generate_action_plan` exposé en F14 (FR-012 brouillon, US8).
- [DEFERRED-7] Money typé pour `cost_money` / `benefit_money` sur `action_step`.
- [DEFERRED-8] Recommandation contextuelle de ressources (US7).

---

## Dépendances

- Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (Polish).
- US2 dépend de US1 (les routes PATCH/GET supposent le service `generate` opérationnel et un plan existant en base).
- Tests TDD par tâche : RED d'abord (T009–T013, T018–T020), GREEN ensuite (T014–T017, T021–T022).

## Parallélisation

- T002, T004, T005, T007, T008 [P] peuvent être codés en parallèle (fichiers distincts) après T003.
- T009, T010, T011, T013 [P] en parallèle dans US1 (tests).
- T023, T024, T027 [P] en parallèle en Polish.

## Stratégie

MVP livré dès la fin de la Phase 4 — 22 tâches actives, 6 de polish, 8 reportées. Chaque US est indépendamment vérifiable.
