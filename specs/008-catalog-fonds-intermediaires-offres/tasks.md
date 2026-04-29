---
description: "Tasks for F08 — Catalogue Fonds, Intermédiaires & Offres"
---

# Tasks: F08 — Catalogue Fonds, Intermédiaires & Offres

**Input**: Design documents from `/specs/008-catalog-fonds-intermediaires-offres/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests**: Required (TDD obligatoire sur `effective_calculator`, intégration backend, smoke E2E frontend).

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Parallélisable (fichier différent, pas de dépendance bloquante).
- **[Story]**: US1..US6 mappées sur spec.md.
- Tous les chemins sont relatifs à la racine du repo.

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Créer la branche `008-catalog-fonds-intermediaires-offres` (déjà fait, vérifier `git branch --show-current`).
- [X] T002 [P] Vérifier que F01–F07 sont mergées et que `backend/.venv` + `pnpm install` côté frontend sont à jour.
- [X] T003 [P] Préparer le squelette d'arborescence backend : `backend/app/models/`, `backend/app/schemas/`, `backend/app/services/`, `backend/app/api/admin/`, `backend/app/api/catalog/`, `backend/app/core/`, `backend/tests/{unit,integration}/`.
- [DEFERRED] T004 [P] Préparer le squelette frontend (frontend déféré post-MVP).

---

## Phase 2: Foundational — Schéma DB & RLS (blocking)

**Purpose**: tables, RLS, ENUMs, helpers SQL — préalables à toute story.

- [X] T010 Migration Alembic `backend/alembic/versions/0008_catalog_fonds_offre.py` (ENUMs + helper `accreditation_is_active`).
- [X] T011 Table `fonds_source` + index + RLS.
- [X] T012 Table `intermediaire` + index + RLS.
- [X] T013 Table `accreditation` + index + RLS + helper SQL.
- [X] T014 Table `offre` + index + UNIQUE(fonds_id, intermediaire_id, name) + RLS.
- [X] T015 `alembic upgrade head` exécuté sur clean DB ; tests verts.
- [X] T016 [P] `backend/app/schemas/critere.py` (Critere, Document).
- [X] T017 [P] `backend/app/schemas/effective.py` (EffectiveLayer, EffectiveResponse).
- [X] T018 [P] Enregistrement registry F06 via `backend/app/api/admin/specs.py`.
- [X] T019 Currencies whitelist : XOF/EUR/USD/GHS/NGN/MAD/GBP supportés (Money typé Pydantic).

---

## Phase 3: User Story 1 — CRUD Fonds source (P1) 🎯 MVP

**Goal**: Admin crée/édite/publie un Fonds avec publish gate (≥1 source verified) et ETag/If-Match.
**Independent test**: cf spec US1 — POST → draft → publish → GET (FR-001, FR-011, FR-012, FR-013).

### Tests US1 (TDD)

- [X] T020 [P] [US1] `tests/integration/admin/test_admin_fonds.py::test_create_draft_returns_201`.
- [X] T021 [P] [US1] `test_publish_requires_verified_source` (gate 422 sources_not_verified).
- [X] T022 [P] [US1] `test_etag_mismatch_returns_412`.
- [X] T023 [P] [US1] `test_audit_log_records_diff` (create + publish actions).

### Implémentation US1

- [X] T024 [US1] Pas de modèle SQLAlchemy : approche SQL via `app/api/admin/_helpers.py` + crud_router F06 réutilisable.
- [X] T025 [US1] `backend/app/schemas/fonds_source.py` (FondsCreate, FondsUpdate, Money) + validators.
- [X] T026 [US1] `backend/app/api/admin/fonds.py` (CRUD + publish + intermediaires comparator).
- [X] T027 [US1] Router monté sous `/admin/fonds` dans `app/main.py` (avant publish/crud génériques).
- [X] T028 [US1] Suite T020–T023 verte (6 tests).

### Frontend US1 — DEFERRED post-MVP

- [DEFERRED] T029–T035 (frontend Vue/Pinia/composables Fonds).

**Checkpoint US1**: API + UI Fonds source CRUD + publish opérationnels et testés.

---

## Phase 4: User Story 2 — CRUD Intermédiaire accrédité (P1)

**Goal**: identique à US1 pour Intermédiaire.
**Independent test**: spec US2.

### Tests US2

- [X] T040 [US2] `test_crud_lifecycle` (POST/GET/PUT/ETag).
- [X] T041 [US2] `test_publish_gate_and_audit`.

### Implémentation US2

- [X] T042 [US2] Approche SQL via helpers (pas de modèle ORM nécessaire).
- [X] T043 [US2] `backend/app/schemas/intermediaire.py`.
- [X] T044 [US2] `backend/app/api/admin/intermediaires.py` (CRUD + publish + fonds comparator).
- [X] T045 [US2] Router monté sous `/admin/intermediaires`.

### Frontend US2 — DEFERRED post-MVP

- [DEFERRED] T046–T049.

**Checkpoint US2**: catalog Intermédiaires opérationnel.

---

## Phase 5: User Story 3 — Accréditations datées et plafonnées (P1)

**Goal**: relation datée `(intermediaire, fonds, valid_from, valid_to, plafond_money, source_id)`. Helper `is_active(at)`. Bloque création Offre sans accréditation active.

### Tests US3

- [X] T050 [US3] `test_create_with_source_and_money`.
- [X] T051 [US3] `test_is_active_helper` paramétré (4 cas : range / open-ended / expired / future).
- [X] T052 [US3] `test_offre_creation_refused_without_active_accreditation` (409 no_active_accreditation).

### Implémentation US3

- [X] T053 [US3] Approche SQL.
- [X] T054 [US3] `backend/app/schemas/accreditation.py` (validation valid_to >= valid_from).
- [X] T055 [US3] `backend/app/api/admin/accreditations.py` (CRUD + `/is_active` + `has_active_accreditation` helper).
- [X] T056 [US3] Router monté ; tests verts.

### Frontend US3 — DEFERRED post-MVP

- [DEFERRED] T057–T060.

**Checkpoint US3**: pivot temporel opérationnel ; pré-requis pour Offre.

---

## Phase 6: User Story 4 — CRUD Offre + calcul effective (P1) ⭐ CŒUR MÉTIER

**Goal**: Offre = couple (Fonds × Intermédiaire) avec accréditation active, calcul `/effective` arbre 2 niveaux déterministe.

### Tests TDD US4 — `effective_calculator` (5 cas d'école, OBLIGATOIRE)

- [X] T070 [US4] `tests/unit/test_effective_calculator.py` 5 cas d'école paramétrés (GCF×BOAD, GCF×UNDP, FEM×PNUD, SUNREF×Ecobank, FNE-CI×RDC).
- [X] T071 [US4] Tests unitaires opérateurs atomiques (min, max, in, not_in, eq, contains).
- [X] T072 [US4] Tests union documents, sum_frais same/mixed currency, sum_delais.

### Tests intégration US4

- [X] T073 [US4] `test_create_offre_requires_active_accreditation` (409 no_active_accreditation).
- [X] T074 [US4] `test_unique_constraint_fonds_inter_name`.
- [X] T075 [US4] `test_get_effective_returns_two_layer_tree` (vérifie max_amount = min(10M,5M) = 5M et délais sum = 90j).
- [X] T076 [US4] `test_publish_gate_offre`.

### Implémentation US4

- [X] T077 [US4] `backend/app/core/effective_calculator.py` (fonctions pures, snapshot_hash sha256 stable).
- [X] T078 [US4] Service intégré directement dans le endpoint `/admin/offres/{id}/effective` (pas de wrapper séparé nécessaire).
- [X] T079 [US4] Approche SQL via helpers (pas de modèle ORM).
- [X] T080 [US4] `backend/app/schemas/offre.py`.
- [X] T081 [US4] `backend/app/api/admin/offres.py` (CRUD + publish + accreditation gate sur INSERT et publish + GET /effective).
- [X] T082 [US4] Router monté ; T070–T076 verts.

### Frontend US4 — DEFERRED post-MVP

- [DEFERRED] T083–T087.

**Checkpoint US4**: pierre angulaire métier livrée et testée sur 5 cas d'école.

---

## Phase 7: Hooks de cohérence (FR-010, FR-015) — DEFERRED post-MVP

- [DEFERRED] T090–T096 (needs_refresh hook, outdated lazy check, recheck-status, frontend refresh).

---

## Phase 8: User Story 5 — Comparateur intermédiaires (P2)

- [PARTIAL] T101 Backend `GET /admin/fonds/{id}/intermediaires` et `GET /admin/intermediaires/{id}/fonds` LIVRÉS (filtrent par accréditation active).
- [DEFERRED] T100, T102, T103 (test dédié + frontend comparator).

---

## Phase 9: User Story 6 — Submission mode (P2)

- [PARTIAL] T111 Backend `effective_calculator` propage deadline (Offre prime sur Fonds) — couvert par `test_compute_effective_offre_deadline_overrides`.
- [DEFERRED] T110 (test integration dédié), T112 (frontend toggle).

---

## Phase 10: Lecture publique PME `/catalog/*` (FR-020) — DEFERRED post-MVP

- [DEFERRED] T120–T124 (nécessite F11 PME profile pour role `pme`).

---

## Phase 11: Polish & cross-cutting

- [DEFERRED] T130 (E2E Playwright frontend).
- [DEFERRED] T131, T132 (perf p95 mesures).
- [X] T133 Coverage ≥ 80 % sur `effective_calculator.py` (84 %) ; F08 modules global = 83 %, projet global = 85.16 %.
- [DEFERRED] T134 (accessibilité bottom sheets, frontend).
- [X] T135 `manual-tests-08.md` documente les flux curl complets.
- [DEFERRED] T136, T137 (OpenAPI matching, constitution gates).

---

## Dependencies (ordre conseillé)

```
Phase 1 (Setup) → Phase 2 (Foundational) → ┬─ Phase 3 (US1 Fonds) ─────────┐
                                            ├─ Phase 4 (US2 Intermédiaire) ─┤
                                            └─ Phase 5 (US3 Accreditation) ─┴→ Phase 6 (US4 Offre) →
   → Phase 7 (Hooks cohérence) → Phase 8 (US5 Comparator) → Phase 9 (US6 Submission) →
   → Phase 10 (Catalog PME) → Phase 11 (Polish)
```

US1, US2, US3 sont parallélisables entre eux après Phase 2. US4 nécessite US1 + US2 + US3.
US5 et US6 nécessitent US4. Phase 10 nécessite US4. Phase 11 finalise.

## Parallel Examples

- Tests TDD US4 (T070–T076) : 7 fichiers indépendants → 7 développeurs parallèles.
- Frontend stores/composables T029, T030, T046, T047, T057, T058, T083, T084 : tous parallélisables.
- Polish T130–T136 : tous indépendants.

## MVP Scope

**MVP = US1 + US2 + US3 + US4 (Phases 1–7)**. Permet à un admin de saisir un catalogue complet (Fonds, Intermédiaires, Accreditations, Offres) avec calcul `/effective` opérationnel, hooks de cohérence et publish gate. US5/US6 et lecture publique sont incrémentaux mais non bloquants pour démo MVP.

## Total tasks

- Phase 1 : 4
- Phase 2 : 10 (T010–T019)
- Phase 3 (US1) : 16 (T020–T035)
- Phase 4 (US2) : 10 (T040–T049)
- Phase 5 (US3) : 11 (T050–T060)
- Phase 6 (US4) : 18 (T070–T087)
- Phase 7 : 7 (T090–T096)
- Phase 8 (US5) : 4 (T100–T103)
- Phase 9 (US6) : 3 (T110–T112)
- Phase 10 : 5 (T120–T124)
- Phase 11 : 8 (T130–T137)

**Total : 96 tâches**.
