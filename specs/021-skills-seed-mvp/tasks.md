# Tasks — Seed des Skills MVP (F21)

**Branch**: `021-skills-seed-mvp` — **Date**: 2026-04-29

Source: spec.md, plan.md, data-model.md, contracts/seed-cli.md.

User stories :
- **US1 (P1)** : Seed des 3 skills critiques.
- **US2 (P1)** : Golden examples seedés.
- **US3 (P2)** : 6+ shells skills additionnelles.
- **US4 (P3)** : Procédure markdown documentée par skill critique.

## Phase 1 — Setup

- [ ] T001 Vérifier que `pyyaml` est importable depuis le venv backend ; si absent, fallback documenté dans `manual-tests-21.md`.
- [ ] T002 Créer arborescence `backend/scripts/seeds/skills/critical/` et `backend/scripts/seeds/skills/shells/`.
- [ ] T003 Vérifier `backend/scripts/__init__.py` (créer si absent) pour rendre le package exécutable via `python -m`.

## Phase 2 — Foundational (bloquants)

- [ ] T010 Implémenter `backend/app/skills/seed_helpers.py` : fonctions pures `content_hash(payload)`, `load_skill_yaml(path)`, `validate_fixture_shape(data)`, `resolve_sources(db, refs)`, `should_publish(...)`, `validate_golden_examples(examples, whitelist)`.
- [ ] T011 [P] Tests unitaires `backend/tests/unit/test_seed_helpers.py` couvrant content_hash stable/changeant, parse YAML, validation shape, validation golden examples.

## Phase 3 — User Story 1 (P1) : Seed des 3 skills critiques

**Goal**: insérer/upserter les 3 skills critiques avec idempotence + statut basé sur sources.
**Independent Test**: lancer le script sur DB → 3 skills critiques en BDD ; relancer → counts inchangés.

- [ ] T020 [US1] Écrire `backend/scripts/seeds/skills/critical/skill_esg_diagnostic.yaml` (sources, activation_rules, tool_whitelist, prompt_expert ≤ 6000 chars, procedure markdown).
- [ ] T021 [P] [US1] Écrire `backend/scripts/seeds/skills/critical/skill_score_gcf.yaml`.
- [ ] T022 [P] [US1] Écrire `backend/scripts/seeds/skills/critical/skill_dossier_gcf_via_boad.yaml`.
- [ ] T023 [US1] Implémenter `backend/scripts/seed_skills.py` (CLI) : args `--force --dry-run --only --seeds-dir`, parcours fixtures, upsert SQLAlchemy table `skill` (clé `name`), gestion `valid_from/created_at/updated_at`, lien `skill_source`, summary JSON. Bump `version` si content_hash change. Skip si tool inconnu, exit 1 final.
- [ ] T024 [US1] Brancher audit log via `app.admin.audit.write_admin_event` (si compatible) ; sinon log structuré.
- [ ] T025 [US1] Tests intégration `backend/tests/integration/test_seed_skills_e2e.py` (pytest+DB) : insertion vide, re-run no-op, modif content_hash → bump, tool inconnu → skip + exit 1, sources non verified → draft.

## Phase 4 — User Story 2 (P1) : Golden examples

**Goal**: chaque skill critique a 5 golden examples valides en JSONB.
**Independent Test**: `jsonb_array_length(golden_examples)` = 5 par skill critique.

- [ ] T030 [US2] Étendre `skill_esg_diagnostic.yaml` avec 5 golden_examples (`expected_tool` dans whitelist, `intent` ∈ {analyse, mutation, navigation, question}).
- [ ] T031 [P] [US2] Étendre `skill_score_gcf.yaml` avec 5 golden_examples.
- [ ] T032 [P] [US2] Étendre `skill_dossier_gcf_via_boad.yaml` avec 5 golden_examples.
- [ ] T033 [US2] Test unitaire `test_seed_helpers.py::test_validate_golden_examples` (cas OK, cas tool hors whitelist, cas < 5).
- [ ] T034 [US2] Test intégration vérifiant qu'après seed chaque critique a exactement 5 entrées.

## Phase 5 — User Story 3 (P2) : Shells additionnelles

**Goal**: insérer ≥ 6 shells en `draft`.
**Independent Test**: count(draft like 'skill_%') ≥ 6 après seed initial.

- [ ] T040 [P] [US3] Créer 8 fixtures shells YAML : skill_score_boad, skill_score_ifc, skill_carbon_calc, skill_dossier_sunref_ecobank, skill_dossier_fem_via_pnud, skill_intermediaire_boad, skill_attestation, skill_credit_score (placeholder prompt, status_target draft, ≥ 1 tool connu).
- [ ] T041 [US3] Étendre `seed_skills.py` pour parcourir aussi `shells/` ; ne JAMAIS rétrograder une skill `published` vers `draft`.
- [ ] T042 [US3] Test intégration : 8 shells en draft après seed initial ; passage manuel d'une shell en published puis re-run conserve published.

## Phase 6 — User Story 4 (P3) : Procédure documentée

**Goal**: champ `procedure` markdown ≥ 200 chars avec étapes numérotées par skill critique.

- [ ] T050 [US4] Compléter le bloc `procedure:` dans les 3 fixtures critiques (≥ 200 chars, étapes 1..N).
- [ ] T051 [US4] Test unitaire vérifiant que `validate_fixture_shape` accepte/rejette selon longueur procedure pour les skills critiques.

## Phase 7 — Polish & cross-cutting

- [ ] T060 Mesurer durée d'exécution sur DB locale ; assertion `duration_ms < 30000` dans test intégration.
- [ ] T061 [P] `pytest --cov` ≥ 80 % sur `backend/scripts/seed_skills.py` + `backend/app/skills/seed_helpers.py`.
- [ ] T062 [P] `ruff check backend/scripts/seed_skills.py backend/app/skills/seed_helpers.py backend/tests/`.
- [ ] T063 Documenter manual tests dans `.cc-runtime/logs/manual-tests-21.md`.

## Dependencies

- Setup (T001-T003) → Foundational (T010-T011) → US1 → US2 → US3 → US4 → Polish.
- T021 ∥ T022 ; T030 ∥ T031 ∥ T032 ; T040 fixtures shells ∥ entre elles ; T061 ∥ T062.

## MVP scope (livrable minimal vert)

US1 + US2 + Polish T061/T062. US3 et US4 différables si pression temps.
