# Tasks — F16 Tools de Visualisation Inline

**Feature**: Tools de Visualisation Inline (F16)
**Branch**: `016-tools-visualisation-inline`
**Reference**: spec.md, plan.md, research.md, data-model.md, contracts/tools-visualisation.md, quickstart.md

> Convention : TDD strict. Pour chaque tool : test rouge → schéma Pydantic minimal vert → tests négatifs (XSS, source_ids, contraintes) → schéma final. Cible couverture ≥ 80 % sur `app/orchestrator/tools/show_*.py` + `_viz_common.py`.

## Phase 1 — Setup

- [x] T001 Vérifier branche `016-tools-visualisation-inline` (pas main).
- [x] T002 Vérifier l'existence du dossier `backend/tests/tools/` (créé en F15).

## Phase 2 — Foundational (prérequis bloquants)

- [x] T003 Tests rouges `backend/tests/tools/test_viz_common.py` couvrant `AltTextMixin` (`alt_text=""` rejeté), `SourceRequiredMixin` (`source_ids=[]` rejeté), `ensure_internal_link` (`/foo` OK, `https://x` lève ValueError).
- [x] T004 Implémenter `backend/app/orchestrator/tools/_viz_common.py` (`AltTextMixin`, `SourceRequiredMixin`, `ensure_internal_link`, import `no_html` depuis `_common`). Faire passer T003.

## Phase 3 — User Story 1 : show_kpi_card (P1)

- [x] T010 [US1] Tests rouges `backend/tests/tools/test_show_kpi_card.py` : positif, rejet XSS sur label/unit/period/alt_text, rejet `source_ids=[]`, rejet `alt_text=""`, sérialisation Decimal en string.
- [x] T011 [US1] Implémenter `backend/app/orchestrator/tools/show_kpi_card.py` (`ShowKpiCardPayload` + `KpiDelta` + `register()`). Faire passer T010.

## Phase 4 — User Story 2 : show_progress_bar (P1) [DEFERRED]

- [ ] T020 [DEFERRED] [US2] Tests rouges `backend/tests/tools/test_show_progress_bar.py` : positif, `target<=0` rejeté, XSS rejeté, `source_ids` requis, Decimal sérialisé.
- [ ] T021 [DEFERRED] [US2] Implémenter `backend/app/orchestrator/tools/show_progress_bar.py`. Faire passer T020.

## Phase 5 — User Story 3 : show_radar_chart (P1)

- [x] T030 [US3] Tests rouges `backend/tests/tools/test_show_radar_chart.py` : positif (5 axes, 2 séries), longueur `values` ≠ `axes` rejetée, > 5 séries rejetée, < 3 axes rejeté, XSS rejeté.
- [x] T031 [US3] Implémenter `backend/app/orchestrator/tools/show_radar_chart.py` (model_validator cross-field). Faire passer T030.

## Phase 6 — User Story 4 : show_bar_chart (P1)

- [x] T040 [P] [US4] Tests rouges `backend/tests/tools/test_show_bar_chart.py` : positif, > 20 barres rejeté, XSS rejeté.
- [x] T041 [US4] Implémenter `backend/app/orchestrator/tools/show_bar_chart.py`. Faire passer T040.

## Phase 7 — User Story 5 : show_line_chart (P1)

- [x] T050 [P] [US5] Tests rouges `backend/tests/tools/test_show_line_chart.py` : positif, > 50 points rejeté, > 5 séries rejeté, XSS rejeté.
- [x] T051 [US5] Implémenter `backend/app/orchestrator/tools/show_line_chart.py`. Faire passer T050.

## Phase 8 — User Story 6 : show_pie_chart / show_donut_chart (P1) [DEFERRED]

- [ ] T060 [DEFERRED] [P] [US6] Tests rouges `backend/tests/tools/test_show_pie_chart.py` : positif, slice négative rejetée, somme 0 rejetée, > 10 slices rejeté, XSS rejeté.
- [ ] T061 [DEFERRED] [US6] Implémenter `backend/app/orchestrator/tools/show_pie_chart.py`.
- [ ] T062 [DEFERRED] [P] [US6] Tests rouges `backend/tests/tools/test_show_donut_chart.py`.
- [ ] T063 [DEFERRED] [US6] Implémenter `backend/app/orchestrator/tools/show_donut_chart.py`.

## Phase 9 — User Story 7 : show_timeline (P1) [DEFERRED]

- [ ] T070 [DEFERRED] [P] [US7] Tests rouges `backend/tests/tools/test_show_timeline.py`.
- [ ] T071 [DEFERRED] [US7] Implémenter `backend/app/orchestrator/tools/show_timeline.py`.

## Phase 10 — User Story 8 : show_comparison_table (P1) [DEFERRED]

- [ ] T080 [DEFERRED] [P] [US8] Tests rouges `backend/tests/tools/test_show_comparison_table.py`.
- [ ] T081 [DEFERRED] [US8] Implémenter `backend/app/orchestrator/tools/show_comparison_table.py`.

## Phase 11 — User Story 9 : show_match_card (P1) [DEFERRED]

- [ ] T090 [DEFERRED] [P] [US9] Tests rouges `backend/tests/tools/test_show_match_card.py`.
- [ ] T091 [DEFERRED] [US9] Implémenter `backend/app/orchestrator/tools/show_match_card.py`.

## Phase 12 — User Story 10 : register_visualisation_tools (P1)

- [x] T100 [US10] Tests rouges `backend/tests/tools/test_register_visualisation_tools.py` : (a) après appel, les 4 tools P1 MVP sont dans `TOOL_REGISTRY`, (b) chaque entrée a un schéma Pydantic et au moins un positive_example, (c) double appel lève ValueError (cohérent avec F15).
- [x] T101 [US10] Étendre `backend/app/orchestrator/tools/__init__.py` : ajouter `register_visualisation_tools()` qui appelle les 4 `register()` P1 MVP livrés. Faire passer T100.

## Phase 13 — Frontend (best-effort, P1) [DEFERRED]

> Reportés en bloc — backend MVP livré vert. Frontend Vue + extension `<ChatMessageRenderer>` à reprendre en PR de suivi.

- [ ] T110 [DEFERRED] [P] [US1] Composant Vue `frontend/app/components/chat/viz/ShowKpiCard.vue`.
- [ ] T111 [DEFERRED] [P] [US3] Composant Vue `frontend/app/components/chat/viz/ShowRadarChart.vue` + composable `_useChartJs.ts` lazy.
- [ ] T112 [DEFERRED] [P] [US4] Composant Vue `frontend/app/components/chat/viz/ShowBarChart.vue`.
- [ ] T113 [DEFERRED] [P] [US5] Composant Vue `frontend/app/components/chat/viz/ShowLineChart.vue`.
- [ ] T114 [DEFERRED] [P] [US6] Composants Vue `ShowPieChart.vue` + `ShowDonutChart.vue`.
- [ ] T115 [DEFERRED] [P] [US2] Composant Vue `ShowProgressBar.vue`.
- [ ] T116 [DEFERRED] [P] [US7] Composant Vue `ShowTimeline.vue`.
- [ ] T117 [DEFERRED] [P] [US8] Composant Vue `ShowComparisonTable.vue`.
- [ ] T118 [DEFERRED] [P] [US9] Composant Vue `ShowMatchCard.vue`.
- [ ] T119 [DEFERRED] [US10] Étendre `frontend/app/components/chat/ChatMessageRenderer.vue` : switch `payload.type` pour les 10 tools.

## Phase 14 — [DEFERRED] P2

- [ ] T200 [DEFERRED] [US11] Implémenter `backend/app/orchestrator/tools/show_map.py` + `backend/tests/tools/test_show_map.py`.
- [ ] T201 [DEFERRED] [US12] Implémenter `backend/app/orchestrator/tools/mermaid_validator.py` (whitelist regex) + `backend/tests/tools/test_mermaid_validator.py`.
- [ ] T202 [DEFERRED] [US12] Implémenter `backend/app/orchestrator/tools/show_mermaid.py` + `backend/tests/tools/test_show_mermaid.py`.
- [ ] T203 [DEFERRED] Étendre `register_visualisation_tools()` pour inclure show_map et show_mermaid.
- [ ] T204 [DEFERRED] [US11] Composant Vue `frontend/app/components/chat/viz/ShowMap.vue` (lazy Leaflet).
- [ ] T205 [DEFERRED] [US12] Composant Vue `frontend/app/components/chat/viz/ShowMermaid.vue` (lazy mermaid).
- [ ] T206 [DEFERRED] [US13] Logique badge "données obsolètes" dans `ShowKpiCard.vue` + `ShowMatchCard.vue` via `payload.rendered_at` vs `entity.updated_at` EventBus F13.

## Phase 15 — Polish

- [x] T300 Couverture F16 = 98.64 % (≥ 80 % cible) sur les 5 fichiers ajoutés (`_viz_common`, `show_kpi_card`, `show_radar_chart`, `show_bar_chart`, `show_line_chart`).
- [x] T301 Lint : `ruff check` zéro erreur sur les fichiers F16 + `__init__.py`.
- [x] T302 Manuel : `.cc-runtime/logs/manual-tests-16.md`.

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
