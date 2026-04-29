# Tasks — F16 Tools de Visualisation Inline

**Feature**: Tools de Visualisation Inline (F16)
**Branch**: `016-tools-visualisation-inline`
**Reference**: spec.md, plan.md, research.md, data-model.md, contracts/tools-visualisation.md, quickstart.md

> Convention : TDD strict. Pour chaque tool : test rouge → schéma Pydantic minimal vert → tests négatifs (XSS, source_ids, contraintes) → schéma final. Cible couverture ≥ 80 % sur `app/orchestrator/tools/show_*.py` + `_viz_common.py`.

## Phase 1 — Setup

- [ ] T001 Vérifier branche `016-tools-visualisation-inline` (pas main).
- [ ] T002 Vérifier l'existence du dossier `backend/tests/tools/` (créé en F15).

## Phase 2 — Foundational (prérequis bloquants)

- [ ] T003 Tests rouges `backend/tests/tools/test_viz_common.py` couvrant `AltTextMixin` (`alt_text=""` rejeté), `SourceRequiredMixin` (`source_ids=[]` rejeté), `ensure_internal_link` (`/foo` OK, `https://x` lève ValueError).
- [ ] T004 Implémenter `backend/app/orchestrator/tools/_viz_common.py` (`AltTextMixin`, `SourceRequiredMixin`, `ensure_internal_link`, import `no_html` depuis `_common`). Faire passer T003.

## Phase 3 — User Story 1 : show_kpi_card (P1)

- [ ] T010 [US1] Tests rouges `backend/tests/tools/test_show_kpi_card.py` : positif, rejet XSS sur label/unit/period/alt_text, rejet `source_ids=[]`, rejet `alt_text=""`, sérialisation Decimal en string.
- [ ] T011 [US1] Implémenter `backend/app/orchestrator/tools/show_kpi_card.py` (`ShowKpiCardPayload` + `KpiDelta` + `register()`). Faire passer T010.

## Phase 4 — User Story 2 : show_progress_bar (P1)

- [ ] T020 [US2] Tests rouges `backend/tests/tools/test_show_progress_bar.py` : positif, `target<=0` rejeté, XSS rejeté, `source_ids` requis, Decimal sérialisé.
- [ ] T021 [US2] Implémenter `backend/app/orchestrator/tools/show_progress_bar.py`. Faire passer T020.

## Phase 5 — User Story 3 : show_radar_chart (P1)

- [ ] T030 [US3] Tests rouges `backend/tests/tools/test_show_radar_chart.py` : positif (5 axes, 2 séries), longueur `values` ≠ `axes` rejetée, > 5 séries rejetée, < 3 axes rejeté, XSS rejeté.
- [ ] T031 [US3] Implémenter `backend/app/orchestrator/tools/show_radar_chart.py` (model_validator cross-field). Faire passer T030.

## Phase 6 — User Story 4 : show_bar_chart (P1)

- [ ] T040 [P] [US4] Tests rouges `backend/tests/tools/test_show_bar_chart.py` : positif, > 20 barres rejeté, XSS rejeté.
- [ ] T041 [US4] Implémenter `backend/app/orchestrator/tools/show_bar_chart.py`. Faire passer T040.

## Phase 7 — User Story 5 : show_line_chart (P1)

- [ ] T050 [P] [US5] Tests rouges `backend/tests/tools/test_show_line_chart.py` : positif, > 50 points rejeté, > 5 séries rejeté, XSS rejeté.
- [ ] T051 [US5] Implémenter `backend/app/orchestrator/tools/show_line_chart.py`. Faire passer T050.

## Phase 8 — User Story 6 : show_pie_chart / show_donut_chart (P1)

- [ ] T060 [P] [US6] Tests rouges `backend/tests/tools/test_show_pie_chart.py` : positif, slice négative rejetée, somme 0 rejetée, > 10 slices rejeté, XSS rejeté.
- [ ] T061 [US6] Implémenter `backend/app/orchestrator/tools/show_pie_chart.py`. Faire passer T060.
- [ ] T062 [P] [US6] Tests rouges `backend/tests/tools/test_show_donut_chart.py` (mêmes contraintes que pie).
- [ ] T063 [US6] Implémenter `backend/app/orchestrator/tools/show_donut_chart.py`. Faire passer T062.

## Phase 9 — User Story 7 : show_timeline (P1)

- [ ] T070 [P] [US7] Tests rouges `backend/tests/tools/test_show_timeline.py` : positif, date format invalide rejeté, status non whitelisté rejeté, > 20 items rejeté, orientation invalide rejetée, XSS rejeté.
- [ ] T071 [US7] Implémenter `backend/app/orchestrator/tools/show_timeline.py`. Faire passer T070.

## Phase 10 — User Story 8 : show_comparison_table (P1)

- [ ] T080 [P] [US8] Tests rouges `backend/tests/tools/test_show_comparison_table.py` : positif (3x5), > 5 colonnes rejeté, > 5 lignes rejeté, longueur row.values ≠ columns rejetée, XSS rejeté.
- [ ] T081 [US8] Implémenter `backend/app/orchestrator/tools/show_comparison_table.py` (model_validator cross-field). Faire passer T080.

## Phase 11 — User Story 9 : show_match_card (P1)

- [ ] T090 [P] [US9] Tests rouges `backend/tests/tools/test_show_match_card.py` : positif, score hors [0,100] rejeté, link externe (`https://`) rejeté, link sans `/` rejeté, XSS rejeté, `source_ids` requis.
- [ ] T091 [US9] Implémenter `backend/app/orchestrator/tools/show_match_card.py`. Faire passer T090.

## Phase 12 — User Story 10 : Message hybride + register_visualisation_tools (P1)

- [ ] T100 [US10] Tests rouges `backend/tests/tools/test_register_visualisation_tools.py` : (a) après appel, les 10 tools P1 sont dans `TOOL_REGISTRY`, (b) chaque entrée a un schéma Pydantic et au moins un positive_example, (c) double appel ne lève pas (idempotence).
- [ ] T101 [US10] Étendre `backend/app/orchestrator/tools/__init__.py` : ajouter `register_visualisation_tools()` qui appelle les 10 `register()` P1. Faire passer T100.

## Phase 13 — Frontend (best-effort, P1)

- [ ] T110 [P] [US1] Composant Vue `frontend/app/components/chat/viz/ShowKpiCard.vue` : props payload, rendu valeur+unit+delta+SourceCite+aria-label.
- [ ] T111 [P] [US3] Composant Vue `frontend/app/components/chat/viz/ShowRadarChart.vue` avec composable `frontend/app/components/chat/viz/_useChartJs.ts` (lazy import chart.js).
- [ ] T112 [P] [US4] Composant Vue `frontend/app/components/chat/viz/ShowBarChart.vue` (réutilise `_useChartJs.ts`).
- [ ] T113 [P] [US5] Composant Vue `frontend/app/components/chat/viz/ShowLineChart.vue`.
- [ ] T114 [P] [US6] Composants Vue `frontend/app/components/chat/viz/ShowPieChart.vue` + `frontend/app/components/chat/viz/ShowDonutChart.vue`.
- [ ] T115 [P] [US2] Composant Vue `frontend/app/components/chat/viz/ShowProgressBar.vue` (CSS pur).
- [ ] T116 [P] [US7] Composant Vue `frontend/app/components/chat/viz/ShowTimeline.vue` (CSS pur).
- [ ] T117 [P] [US8] Composant Vue `frontend/app/components/chat/viz/ShowComparisonTable.vue`.
- [ ] T118 [P] [US9] Composant Vue `frontend/app/components/chat/viz/ShowMatchCard.vue` (CTA `<NuxtLink>`).
- [ ] T119 [US10] Étendre `frontend/app/components/chat/ChatMessageRenderer.vue` : ajouter switch `payload.type` pour les 10 tools P1.

## Phase 14 — [DEFERRED] P2

- [ ] T200 [DEFERRED] [US11] Implémenter `backend/app/orchestrator/tools/show_map.py` + `backend/tests/tools/test_show_map.py`.
- [ ] T201 [DEFERRED] [US12] Implémenter `backend/app/orchestrator/tools/mermaid_validator.py` (whitelist regex) + `backend/tests/tools/test_mermaid_validator.py`.
- [ ] T202 [DEFERRED] [US12] Implémenter `backend/app/orchestrator/tools/show_mermaid.py` + `backend/tests/tools/test_show_mermaid.py`.
- [ ] T203 [DEFERRED] Étendre `register_visualisation_tools()` pour inclure show_map et show_mermaid.
- [ ] T204 [DEFERRED] [US11] Composant Vue `frontend/app/components/chat/viz/ShowMap.vue` (lazy Leaflet).
- [ ] T205 [DEFERRED] [US12] Composant Vue `frontend/app/components/chat/viz/ShowMermaid.vue` (lazy mermaid).
- [ ] T206 [DEFERRED] [US13] Logique badge "données obsolètes" dans `ShowKpiCard.vue` + `ShowMatchCard.vue` via `payload.rendered_at` vs `entity.updated_at` EventBus F13.

## Phase 15 — Polish

- [ ] T300 Couverture : `pytest -q tests/tools/ --cov=app/orchestrator/tools --cov-report=term-missing` ≥ 80 % sur fichiers F16.
- [ ] T301 Lint : `ruff check app/orchestrator/tools/ tests/tools/` zéro erreur.
- [ ] T302 Manuel : exécuter le quickstart REPL puis loguer dans `.cc-runtime/logs/manual-tests-16.md`.

## Dépendances et ordre

- Phase 1 (T001-T002) bloquante.
- Phase 2 (T003-T004) bloquante pour toutes les phases US.
- Phases 3-11 indépendantes deux à deux côté backend (fichiers différents) — parallélisables.
- Phase 12 (T100-T101) dépend des Phases 3-11.
- Phase 13 frontend dépend de Phase 12.
- Phase 14 [DEFERRED].
- Phase 15 finale.

## Parallélisation

Tasks `[P]` (T040, T050, T060, T062, T070, T080, T090, T110-T118) ciblent des fichiers différents et peuvent s'exécuter en parallèle.

## Stratégie MVP

**MVP minimal** : Phases 1, 2, 3, 12, 15 → 1 tool (`show_kpi_card`) + register + couverture.
**MVP étendu (cible F16)** : Phases 1-12 + Phase 15 ; Phase 13 best-effort.
**Si budget dépassé** : reporter Phase 13 ; Phase 14 reste DEFERRED.
