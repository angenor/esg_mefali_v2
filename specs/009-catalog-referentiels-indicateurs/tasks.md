---
description: "Task list for F09 Catalogue Référentiels, Indicateurs, Critères, Documents Requis, Facteurs d'Émission"
---

# Tasks: F09 — Catalogue Référentiels, Indicateurs, Critères, Documents Requis, Facteurs d'Émission

**Input**: Design documents from `/specs/009-catalog-referentiels-indicateurs/`
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story (US1..US7) or `INF` (infra/transverse)

---

## Phase A — Foundation (INF, blocks all stories)

- [ ] T001 [INF] Créer migration Alembic `backend/alembic/versions/XXXX_f09_catalog.py` : 6 tables + enums + UNIQUE/CHECK + index `idx_facteur_emission_lookup` + RLS policies + trigger valid_to facteur_emission (cf data-model.md).
- [ ] T002 [INF] [P] Modèles SQLAlchemy : `backend/app/models/indicateur.py`, `referentiel.py`, `referentiel_indicateur.py`, `critere.py`, `document_requis.py`, `facteur_emission.py` (5 fichiers parallèles + 1 jonction).
- [ ] T003 [INF] Étendre `backend/app/admin/registry.py` pour enregistrer les 5 entités F09 (codes, perms admin, hooks publish).
- [ ] T004 [INF] Test integration `backend/tests/integration/test_rls_catalogue.py` : admin voit draft+published, pme voit published only sur les 5 entités (FR-011).

## Phase B — User Story 1 : CRUD Indicateurs (P1)

- [ ] T010 [US1] Schémas Pydantic v2 strict `backend/app/catalog/indicateurs/schemas.py` (Create/Update/Out + value_type CHECK + enum_values requis si enum).
- [ ] T011 [US1] [P] Service `backend/app/catalog/indicateurs/service.py` : create/update/list/publish/archive avec sourcing gate (≥1 source verified) + If-Match versioning.
- [ ] T012 [US1] [P] Permissions `backend/app/catalog/indicateurs/permissions.py` : admin only `/admin/*`.
- [ ] T013 [US1] Router `backend/app/catalog/indicateurs/router.py` : enregistrement via crud_router F06 + endpoint `GET /admin/indicateurs?pillar=&search=&status=` paginé (FR-002).
- [ ] T014 [US1] [P] Tests `backend/tests/catalog/indicateurs/test_crud.py` (create/list/patch/delete).
- [ ] T015 [US1] [P] Tests `backend/tests/catalog/indicateurs/test_publish_gate.py` : refus si pas de source verified (FR-013).
- [ ] T016 [US1] [P] Tests `backend/tests/catalog/indicateurs/test_versioning.py` : modifier published → v2 draft via publish_new_version + If-Match.
- [ ] T017 [US1] Page admin Nuxt `frontend/app/pages/admin/catalogue/indicateurs/index.vue` : liste + filtres + bottom sheet création.
- [ ] T018 [US1] [P] Page detail `frontend/app/pages/admin/catalogue/indicateurs/[id].vue` : edit + publish.
- [ ] T019 [US1] [P] Composable `frontend/app/composables/useIndicateurs.ts`.
- [ ] T020 [US1] [P] E2E `frontend/tests/e2e/indicateurs.crud.spec.ts`.

## Phase C — User Story 2 : CRUD Référentiels + /full + lookup (P1)

- [ ] T030 [US2] Schémas `backend/app/catalog/referentiels/schemas.py` (Referentiel + ReferentielIndicateur attach/detach).
- [ ] T031 [US2] Service `backend/app/catalog/referentiels/service.py` : CRUD + endpoint `/full` jointures (FR-003).
- [ ] T032 [US2] [P] Helper `get_referentiel(code, version=None)` (FR-008) dans `backend/app/catalog/referentiels/service.py`.
- [ ] T033 [US2] Router `backend/app/catalog/referentiels/router.py` : CRUD + `POST /admin/referentiels/{id}/indicateurs` attach/detach + `/full`.
- [ ] T034 [US2] [P] Tests `backend/tests/catalog/referentiels/test_crud.py`.
- [ ] T035 [US2] [P] Tests `backend/tests/catalog/referentiels/test_full_endpoint.py` : payload joint complet, performance < 1s sur 30 indicateurs.
- [ ] T036 [US2] [P] Page admin Nuxt `frontend/app/pages/admin/catalogue/referentiels/index.vue`.
- [ ] T037 [US2] [P] Composable `frontend/app/composables/useReferentiels.ts`.

## Phase D — User Story 3 : Critères + DSL (P1)

- [ ] T040 [US3] Schémas DSL strict `backend/app/catalog/criteres/schemas.py` (Pydantic recursive `extra='forbid'`, profondeur ≤ 6, payload ≤ 8 KB).
- [ ] T041 [US3] Module `backend/app/catalog/criteres/dsl.py` : parser + evaluator tri-state (true/false/undecidable), 11 opérateurs.
- [ ] T042 [US3] Service `backend/app/catalog/criteres/service.py` : CRUD + filtre `owner_type/owner_id` trié par severity (FR-009).
- [ ] T043 [US3] [P] Router `backend/app/catalog/criteres/router.py` + endpoint `POST /admin/criteres/{id}/evaluate`.
- [ ] T044 [US3] [P] Tests `backend/tests/catalog/criteres/test_dsl_parser.py` : 10 cas d'évaluation couvrant les 11 opérateurs (SC-005).
- [ ] T045 [US3] [P] Tests `backend/tests/catalog/criteres/test_dsl_sandbox.py` : fuzzing négatif (op inconnu, profondeur > 6, payload > 8 KB, eval injection) — vérifier rejet (NFR-002).
- [ ] T046 [US3] [P] Tests `backend/tests/catalog/criteres/test_owner_filter.py`.
- [ ] T047 [US3] Page admin Nuxt `frontend/app/pages/admin/catalogue/criteres/index.vue` + `[id].vue` (textarea JSON + validation).
- [ ] T048 [US3] [P] Composable `frontend/app/composables/useCriteres.ts`.

## Phase E — User Story 4 : Documents Requis (P1)

- [ ] T050 [US4] Schémas + service + router `backend/app/catalog/documents_requis/{schemas,service,router}.py` ; filtre `owner_type/owner_id` (FR-010) ; condition `required_when` réutilise DSL.
- [ ] T051 [US4] [P] Tests `backend/tests/catalog/documents_requis/test_crud.py`.
- [ ] T052 [US4] [P] Page admin Nuxt + composable `useDocumentsRequis`.

## Phase F — User Story 5 : Facteurs d'émission + lookup (P1)

- [ ] T060 [US5] Schémas + service + router `backend/app/catalog/facteurs_emission/{schemas,service,router}.py` avec UNIQUE `(code,pays_iso2,valid_from)` + auto-clôture valid_to.
- [ ] T061 [US5] Helper `get_facteur(code, pays_iso2=None, at=None)` dans `backend/app/catalog/facteurs_emission/lookup.py` (FR-007 + fallback pays exact → mondial → 404).
- [ ] T062 [US5] [P] Tests `backend/tests/catalog/facteurs_emission/test_crud.py`.
- [ ] T063 [US5] [P] Tests `backend/tests/catalog/facteurs_emission/test_lookup_helper.py` (résolution par date + fallback pays).
- [ ] T064 [US5] [P] Tests `backend/tests/catalog/facteurs_emission/test_validity_window.py` (auto-clôture v1 quand v2 inserrée).
- [ ] T065 [US5] [P] Page admin Nuxt + composable `useFacteursEmission`.

## Phase G — User Story 6 : Page visualisation Référentiel /full (P2)

- [ ] T070 [US6] Page detail `frontend/app/pages/admin/catalogue/referentiels/[id].vue` : header + table indicateurs liés + sources + sélecteur versions + bottom sheet edit.
- [ ] T071 [US6] [P] E2E `frontend/tests/e2e/referentiels.full.spec.ts` : SC-007 charge < 1 s pour 30 indicateurs.

## Phase H — User Story 7 : Validateur publish Référentiel (P2)

- [ ] T080 [US7] Module `backend/app/catalog/referentiels/validator.py` : (a) somme poids = 100 ± 0.01, (b) sources verified, (c) indicateurs published, (d) formula custom non vide si custom.
- [ ] T081 [US7] Brancher validator dans `POST /admin/referentiels/{id}/publish` (FR-005) → 409 + payload structuré.
- [ ] T082 [US7] [P] Tests `backend/tests/catalog/referentiels/test_publish_validator.py` : SC-004 (rejet en < 200 ms, liste exhaustive des défauts).

## Phase I — Audit + verification

- [ ] T090 [INF] Brancher décorateur audit F04 sur les 5 services (create/update/publish/archive/delete) — `source_of_change='admin'`.
- [ ] T091 [INF] Test integration `backend/tests/integration/test_audit_versioning_chain.py` : modifier indicateur published → v2 draft + audit append-only complet.

## Phase J — Seed + smoke

- [ ] T100 [INF] [P] Script `backend/app/scripts/seed_f09_minimal.py` (cf quickstart.md).
- [ ] T101 [INF] Smoke tests CLI : `python -c "from app.catalog.referentiels.service import get_referentiel; ..."` et `get_facteur(...)`.

---

## Dependencies graph

- T001-T004 (Phase A) bloquent toutes les autres phases.
- T010-T020 (US1) indépendant des US2-US5 mais requis comme prérequis pour T030-T037 (US2 référence indicateurs publiés) et T040-T048 (US3 référence indicateurs publiés via DSL).
- T080-T081 (US7 validator) doivent être livrés AVANT que `POST /referentiels/{id}/publish` (US2 acceptance #2) soit fonctionnel ; en pratique, T080-T081 s'exécutent en parallèle de T030-T033 mais T031/T033 doivent l'invoquer dès qu'il existe (intégration en T081). T082 tests viennent ensuite. T010-T016 (US1) restent prérequis pour pouvoir tester un référentiel avec indicateurs publiés.
- T090-T091 dépendent que tous les services existent.
- T100-T101 en dernier.

## Total : 47 tâches

≤ 60 → exécution complète recommandée. Pas besoin de stratégie MVP ≤ 50 (le compte respecte le seuil).
