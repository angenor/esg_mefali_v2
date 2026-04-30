# Tasks: F26 — Générateur de Dossiers de Candidature

**Branch**: `026-generateur-dossiers-candidatures` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Convention

- `[T###]` ID — `[P]` parallélisable — description.
- TDD : tests rouges → implémentation → vert → refactor.

## Phase A — Migration + modèles

- [T001] Créer `backend/alembic/versions/0018_f26_template_dossier_dossier.py` (CREATE TABLE `template_dossier`, `dossier`, indexes, RLS sur `dossier` par `account_id`).
- [T002] [P] Créer `backend/app/models/template_dossier.py`.
- [T003] [P] Créer `backend/app/models/dossier.py`.
- [T004] Mettre à jour `backend/app/models/__init__.py` (exports).

## Phase B — Schemas + utilitaires

- [T005] [P] Créer `backend/app/dossier/__init__.py`.
- [T006] [P] Créer `backend/app/dossier/schemas.py` (Pydantic).
- [T007] [P] Créer `backend/tests/unit/dossier/test_source_extractor.py` (RED).
- [T008] Implémenter `backend/app/dossier/source_extractor.py` (regex `[[source:UUID]]`, dédup ensembliste).
- [T009] [P] Créer `backend/tests/unit/dossier/test_validators.py` (RED).
- [T010] Implémenter `backend/app/dossier/validators.py` (règle "chiffre → ≥1 source").

## Phase C — Pré-remplissage

- [T011] [P] Créer `backend/tests/unit/dossier/test_prefill.py` (RED).
- [T012] Implémenter `backend/app/dossier/prefill.py` couvrant `identite_entreprise`, `description_projet`, `indicateurs_impact`, `plan_financement` (Money typé).

## Phase D — LLM writer + service

- [T013] [P] Créer `backend/app/dossier/llm_writer.py` : interface `LLMNarrativeWriter` + impl `EchoNarrativeWriter`.
- [T014] [P] Créer `backend/tests/unit/dossier/test_service.py` (RED).
- [T015] Implémenter `backend/app/dossier/repository.py`.
- [T016] Implémenter `backend/app/dossier/service.py` (`generate`, `read`, `edit_section`, `regenerate_section`).

## Phase E — Checklist + exporter

- [T017] [P] Créer `backend/tests/unit/dossier/test_checklist.py` (RED).
- [T018] Implémenter `backend/app/dossier/checklist_service.py`.
- [T019] [P] Créer `backend/tests/unit/dossier/test_exporter_smoke.py` (RED).
- [T020] Implémenter `backend/app/dossier/exporter.py`.

## Phase F — Router FastAPI

- [T021] [P] Créer `backend/tests/integration/dossier/test_routes.py` (RED).
- [T022] [P] Créer `backend/tests/integration/dossier/test_admin_template_routes.py` (RED).
- [T023] Implémenter `backend/app/dossier/router.py` (6 endpoints PME + 3 endpoints admin template).
- [T024] Modifier `backend/app/main.py` : `include_router`.

## Phase G — RLS + audit + tool LLM

- [T025] [P] Créer `backend/tests/integration/dossier/test_rls.py` (RED).
- [T026] Vérifier policies RLS via migration et fixture commune.
- [T027] [P] Créer `backend/tests/integration/dossier/test_audit.py` (RED).
- [T028] [P] Créer `backend/tests/unit/dossier/test_tool.py` (RED).
- [T029] Implémenter `backend/app/dossier/tool.py`.

## Phase H — Validation finale

- [T030] `pytest backend/tests/unit/dossier backend/tests/integration/dossier --cov=app.dossier --cov-fail-under=80`.
- [T031] `ruff check backend/app/dossier backend/tests/unit/dossier backend/tests/integration/dossier`.
- [T032] Log manuel `.cc-runtime/logs/manual-tests-26.md`.
- [T033] Commit final.

## DEFERRED

- Frontend Nuxt (`/profil/candidatures/[id]/dossier`).
- EN exhaustif (skill EN).
- Streaming SSE par section.
- Génération multi-candidatures parallèle (US9).
- Inclusion attestation ESG (US10) — F30 pas livrée.

## Mapping Spec → Tasks

- US1 (générer) → T001..T024.
- US2 (pré-remplir) → T011, T012.
- US3 (sections narratives skill) → T013, T014, T016.
- US4 (édition + regénération) → T016, T021, T023.
- US5 (multilangue FR/EN) → T016, T021.
- US6 (checklist) → T017, T018, T021.
- US7 (export Word/PDF) → T019, T020, T021.
- US8 (annexe sources) → T007, T008, T016.
- US9 — DEFERRED.
- US10 — DEFERRED.

## Mapping FR → Tasks

| FR | Tâches |
|----|-------|
| FR-001 | T001, T002, T006 |
| FR-002 | T015, T022, T023 |
| FR-003 | T011..T016 |
| FR-004 | T001, T003, T015 |
| FR-005 | T021, T023 |
| FR-006 | T016, T021 |
| FR-007 | T016, T021 |
| FR-008 | T007, T008, T016 |
| FR-009 | T017, T018 |
| FR-010 | T019, T020 |
| FR-011 | T009, T010, T016 |
| FR-012 | T001 (RLS), T025, T026 |
| FR-013 | T016, T020, T027 |
| FR-014 | T028, T029 |
| FR-015 | DEFERRED |
| FR-016 | DEFERRED |
