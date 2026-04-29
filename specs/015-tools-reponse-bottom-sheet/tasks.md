---
description: "F15 task list"
---

# Tasks: F15 — Tools de Réponse en Bottom Sheet

**Input** : `specs/015-tools-reponse-bottom-sheet/{spec.md, plan.md, contracts/tools-schemas.md}`

**Tests** : OUI — tests Pydantic + tests d'enregistrement.

## Path Conventions

- Backend : `backend/app/orchestrator/tools/`, `backend/tests/tools/`.
- Frontend : `frontend/app/components/chat/` — **DEFERRED**.

## Phase 1 : Setup

- T001 [P] Créer `backend/app/orchestrator/tools/__init__.py` (placeholder pour `register_response_tools`).
- T002 [P] Créer `backend/tests/tools/__init__.py` et `backend/tests/tools/conftest.py` (fixture `clean_registry`).
- T003 Créer `backend/app/orchestrator/tools/_common.py` : `Option` BaseModel + `_no_html` validator.

## Phase 2 : Foundational — adapter F14

- T010 Modifier `backend/app/orchestrator/fixtures_tools.py` : retirer `ask_qcu`, `ask_yes_no`, `show_summary_card`. Conserver `update_demo_profile`, `search_demo_source`.
- T011 Mettre à jour `backend/tests/orchestrator/test_payload_validator.py` : tests migrent vers nouveaux payloads riches.
- T012 Mettre à jour `backend/tests/orchestrator/test_tool_selector.py` : appeler en plus `register_response_tools()`.

## Phase 3 : US1 — ask_qcu (P1) [TDD]

- T100 [P] [US1] `tests/tools/test_ask_qcu.py` — schéma valide, refus extra, refus options<2 ou >7, refus HTML.
- T101 [US1] `app/orchestrator/tools/ask_qcu.py` + `register()`.

## Phase 4 : US2 — ask_qcm (P1)

- T200 [P] [US2] `tests/tools/test_ask_qcm.py` — min/max validator, options 2..20.
- T201 [US2] `app/orchestrator/tools/ask_qcm.py` + `register()`.

## Phase 5 : US3 — ask_yes_no (P1)

- T300 [P] [US3] `tests/tools/test_ask_yes_no.py` — defaults, custom labels.
- T301 [US3] `app/orchestrator/tools/ask_yes_no.py` + `register()`.

## Phase 6 : US4 — ask_select (P1)

- T400 [P] [US4] `tests/tools/test_ask_select.py` — XOR options/endpoint, multi.
- T401 [US4] `app/orchestrator/tools/ask_select.py` + `register()`.

## Phase 7 : US5 — ask_number (P1)

- T500 [P] [US5] `tests/tools/test_ask_number.py` — min<=max, step>0, money currency.
- T501 [US5] `app/orchestrator/tools/ask_number.py` + `register()`.

## Phase 8 : US8 — ask_file_upload (P1)

- T800 [P] [US8] `tests/tools/test_ask_file_upload.py` — entity_type, accepted_mime, max_size_mb.
- T801 [US8] `app/orchestrator/tools/ask_file_upload.py` + `register()`.

## Phase 9 : US10 — show_summary_card (P1)

- T900 [P] [US10] `tests/tools/test_show_summary_card.py` — actions kind, fields 1..30.
- T901 [US10] `app/orchestrator/tools/show_summary_card.py` + `register()`.

## Phase 10 : Tools P2 — DEFERRED si budget

- T1000 [P2] [DEFERRED] `ask_date.py` + `ask_date_range` + tests.
- T1001 [P2] [DEFERRED] `ask_rating.py` + tests.
- T1002 [P2] [DEFERRED] `show_form.py` + tests.

## Phase 11 : Intégration

- T1100 [US12] `app/orchestrator/tools/__init__.py:register_response_tools()` appelle chaque `register()` P1.
- T1101 [US12] `tests/tools/test_register_response_tools.py` : `TOOL_REGISTRY` contient les noms attendus.
- T1102 [US12] Brancher `register_response_tools()` dans `backend/app/main.py` au startup.

## Phase 12 : Frontend — [DEFERRED]

- T1200..T1299 [DEFERRED] composants `<ChatBottomSheet>`, `<AskQcu>`, etc.

## Phase 13 : Validation finale

- T1300 `pytest -q --cov=app/orchestrator/tools --cov-report=term-missing tests/tools/ tests/orchestrator/`.
- T1301 `ruff check app/ tests/`.
- T1302 Vérifier non-régression `tests/chat/`, `tests/orchestrator/`, `tests/projets/`.
- T1303 Logger résultats dans `.cc-runtime/logs/manual-tests-15.md`.

## DEFERRED summary

- Frontend complet (UI US1-US12) : DEFERRED.
- Tools P2 (`ask_date`, `ask_date_range`, `ask_rating`, `show_form`) : DEFERRED si nécessaire.
- Validation client miroir (zod/valibot) : DEFERRED itération 2.
- Virtualisation listes longues : DEFERRED itération 2.
