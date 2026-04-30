# Tasks: F34 — Extension Guidage / Suivi Candidatures / Notifications / Recommandations

**Feature**: 034-extension-guidage-suivi-notifications
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

Toutes les tâches sont backend Python (FastAPI + SQLAlchemy + Alembic + Pydantic v2). TDD-first.

---

## Phase 1 — Setup

- [ ] T001 Vérifier que le venv backend est actif et `pytest` opérationnel.
- [ ] T002 [P] Créer les répertoires `backend/app/notifications/`, `backend/app/candidatures/`, `backend/tests/notifications/`, `backend/tests/candidatures/`.

## Phase 2 — Foundational (bloquant)

- [ ] T003 Créer la migration Alembic `backend/alembic/versions/f034_notification_table.py` (table `notification` + contrainte `chk_notification_kind` + index + RLS policy `account_id = current_setting('app.account_id', true)::uuid`).
- [ ] T004 [P] Créer le modèle SQLAlchemy `backend/app/models/notification.py` et l'exposer via `backend/app/models/__init__.py`.
- [ ] T005 [P] Définir l'enum `NotificationKind` (Pydantic Literal des 5 valeurs MVP) dans `backend/app/notifications/schemas.py`.

---

## Phase 3 — User Story 1 (P1) Suivi des candidatures actives

**Goal**: `GET /me/candidatures` liste les candidatures non supprimées de la PME courante (slice 200, tri updated_at DESC).

**Independent test**: 2 candidatures pour PME A, 1 pour PME B → A reçoit 2 lignes triées DESC, B reçoit 1.

- [ ] T006 [US1] Tests service `backend/tests/candidatures/test_candidatures_service.py` (tri, exclusion deleted, isolation account_id, dérivation progression_pct).
- [ ] T007 [US1] Tests API `backend/tests/candidatures/test_candidatures_api.py` (vide, 2 lignes, isolation tenant, 401 sans auth).
- [ ] T008 [US1] Implémenter `backend/app/candidatures/service.py` (`list_for_account(db, account_id, limit=200)`).
- [ ] T009 [US1] Implémenter `backend/app/candidatures/schemas.py` (`CandidatureRowOut`).
- [ ] T010 [US1] Implémenter `backend/app/candidatures/router.py` (`GET /me/candidatures` + `Depends(get_current_pme)`).
- [ ] T011 [US1] Brancher le router dans `backend/app/main.py`.
- [ ] T012 [US1] Lancer pytest sur ce module → vert.

---

## Phase 4 — User Story 2 (P1) Mise à jour du statut de candidature

**Goal**: `PATCH /me/candidatures/{id}/status` accepte 5 valeurs, audite, isole.

**Independent test**: PATCH brouillon→soumise → 200, version+1, audit log écrit. PATCH cross-tenant → 404.

- [ ] T013 [US2] Tests API `backend/tests/candidatures/test_candidatures_status_api.py` (statut OK, statut hors liste 422, cross-tenant 404, deleted 404, audit log présent).
- [ ] T014 [US2] Étendre `backend/app/candidatures/schemas.py` (`CandidatureStatusUpdateIn`, `CandidatureStatusOut`).
- [ ] T015 [US2] Étendre `backend/app/candidatures/service.py` (`update_status` avec ownership check, version++, `record_audit`).
- [ ] T016 [US2] Étendre `backend/app/candidatures/router.py` (`PATCH /me/candidatures/{id}/status`).
- [ ] T017 [US2] Lancer pytest → vert.

---

## Phase 5 — User Story 3 (P1) Centre de notifications PME

**Goal**: table `notification` + endpoints GET / PATCH read + service réutilisable `NotificationService`.

**Independent test**: 2 notifications (1 lue, 1 non lue) → GET retourne 2, `?unread=true` retourne 1, PATCH read sur la non-lue → 200, n'apparaît plus dans `unread`.

- [ ] T018 [US3] Tests service `backend/tests/notifications/test_notifications_service.py` (`create_for_account`, `list_for_account` (tri/unread/limit/offset), `mark_read` idempotent, 404 cross-tenant).
- [ ] T019 [US3] Tests API `backend/tests/notifications/test_notifications_api.py` (GET sans filtre, GET unread, GET limit/offset, PATCH read OK / cross-tenant 404, audit log).
- [ ] T020 [US3] Implémenter `backend/app/notifications/service.py` (`NotificationService.create_for_account / list_for_account / mark_read` + audit best-effort wrapper).
- [ ] T021 [US3] Implémenter `backend/app/notifications/schemas.py` (`NotificationOut`, `NotificationListQuery`).
- [ ] T022 [US3] Implémenter `backend/app/notifications/router.py` (`GET /me/notifications`, `PATCH /me/notifications/{id}/read`).
- [ ] T023 [US3] Brancher le router dans `backend/app/main.py`.
- [ ] T024 [US3] Lancer pytest → vert.

---

## Phase 6 — User Story 4 (P1) Recommandations d'Offres depuis URL

**Goal**: `GET /me/extension/offres-recommandees?url=` retourne max 10 Offres compatibles, score F25 ou fallback 0.0.

**Independent test**: URL gcf.org avec PME ayant projet → liste non vide DESC ; URL inconnue → 200 [] ; sans param → 422.

- [ ] T025 [US4] Tests `backend/tests/extension/test_offres_recommandees.py` (URL valide, URL inconnue, param manquant, isolation, fallback score).
- [ ] T026 [US4] Implémenter `backend/app/extension/recommendations.py` (`recommend_offres_for_url`).
- [ ] T027 [US4] Étendre `backend/app/extension/schemas.py` (`OffreRecommandeeOut`).
- [ ] T028 [US4] Ajouter la route dans `backend/app/extension/router.py` (`GET /extension/offres-recommandees`).
- [ ] T029 [US4] Lancer pytest → vert.

---

## Phase 7 — Polish & couverture

- [ ] T030 [P] Test d'intégration RLS `backend/tests/notifications/test_rls_isolation.py` (fuite = 0 entre 2 PME).
- [ ] T031 [P] Vérifier couverture ≥ 80 % sur les modules ajoutés via `pytest --cov`.
- [ ] T032 `ruff check` + `black --check` sur les modules touchés.
- [ ] T033 Compléter `.cc-runtime/logs/manual-tests-34.md` (scénarios curl).

---

## Dependencies

- Phase 1 → Phase 2 → Phases 3-6 (parallèles entre US3 et US4) → Phase 7.
- US1 (T006-T012) avant US2 (T013-T017) (réutilisation service.py).
- US3 (T018-T024) indépendante de US1/US2.
- US4 (T025-T029) indépendante (utilise `url_matcher` F33).

## Parallel execution opportunities

- T004 et T005 en parallèle après T003.
- US3 et US4 développables en parallèle.
- T030 et T031 en parallèle dans la Phase 7.

## Suggested MVP scope

US1 + US2 + US3 obligatoires. US4 prioritaire mais peut être livré [DEFERRED] si contrainte de temps.
