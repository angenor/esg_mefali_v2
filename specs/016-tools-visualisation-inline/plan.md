# Implementation Plan: Tools de Visualisation Inline (F16)

**Branch**: `016-tools-visualisation-inline` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-tools-visualisation-inline/spec.md`

## Summary

Ajout de 10 tools de visualisation P1 (`show_kpi_card`, `show_progress_bar`, `show_radar_chart`, `show_bar_chart`, `show_line_chart`, `show_pie_chart`, `show_donut_chart`, `show_timeline`, `show_comparison_table`, `show_match_card`) et 2 tools P2 (`show_map`, `show_mermaid`) au catalogue LLM, rendus inline dans la bulle assistant. Backend : schémas Pydantic v2 stricts (`extra="forbid"` + validators anti-XSS, `source_ids` obligatoire sur tools chiffrés, `alt_text` obligatoire), enregistrement dans le `TOOL_REGISTRY` global F14 via `register_visualisation_tools()`. Frontend : composants Vue par tool avec lazy import de chart.js / leaflet / mermaid + extension du dispatcher `<ChatMessageRenderer>` (F13). Aucune nouvelle table : payload stocké dans `chat_message.payload_json` (F13). Validation Mermaid backend = whitelist regex (MVP). Réactivité historique (US13) = badge front via comparaison `updated_at`.

**Scope MVP livré** : tous les schémas Pydantic backend P1 (10 tools) + tests unitaires couvrant ≥ 80 % du code F16 ajouté + `register_visualisation_tools()`. P2 (`show_map`, `show_mermaid`, US13) déferré si budget temps dépassé. Frontend Vue : stubs minimaux + extension `<ChatMessageRenderer>` si possible, sinon [DEFERRED] avec test backend complet.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x / Node 20 (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, pytest + pytest-asyncio (backend) ; Nuxt 4, Vue 3, Tailwind v4, chart.js (lazy), Leaflet (lazy P2), Mermaid (lazy P2), Vitest (frontend)
**Storage**: PostgreSQL 16 + pgvector — réutilisation pure de `chat_message.payload_json` (JSONB) et `source` (F03/F13). Aucune migration.
**Testing**: pytest pour les schémas Pydantic (positive cases, XSS rejection, source_ids manquant, contraintes de taille). Vitest pour les composants Vue (snapshot + accessibilité aria-label) — best-effort.
**Target Platform**: Backend Linux (Europe/AfO), Frontend SSR + SPA Nuxt 4
**Project Type**: Web application (backend + frontend monorepo)
**Performance Goals**: Rendu radar < 200 ms ; bundle initial Nuxt < 500 KB (chart.js / leaflet / mermaid lazy)
**Constraints**: Aucune nouvelle table, aucune migration. Réutilisation stricte de F13/F14/F15. Anti-XSS via `no_html` partagé (F15). `source_ids` non vide obligatoire sur tools chiffrés. `alt_text` non vide obligatoire (accessibilité).
**Scale/Scope**: 12 tools déclarés (10 P1 + 2 P2). 10 schémas Pydantic backend MVP ; 12 composants Vue côté frontend ; 1 fonction `register_visualisation_tools()` ; 1 module de validation Mermaid (whitelist regex P2).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | `source_ids: list[int]` non vide obligatoire sur tous les tools affichant des chiffres (KPI, progress, radar, bar, line, pie, donut, comparison_table, match_card) — FR-004, FR-008. `<SourceCite>` (F03) en coin du composant Vue. | ✅ |
| P2 | Multi-tenant RLS | Aucune nouvelle table. Lecture indirecte de `source` via `source_ids` reste sous RLS F03. | ✅ |
| P3 | Audit log append-only | Aucune mutation introduite — les payloads sont produits par le LLM puis écrits via le pipeline F13 qui journalise déjà `chat_message`. | ✅ |
| P4 | Versioning + snapshot candidatures | Pas de référentiel/critère/formule créé. Pas de candidature mutée. | ✅ |
| P5 | Money typé | Tout champ monétaire éventuel utilise `Money = {amount: Decimal, currency}`. Les `value` numériques génériques sont typées `Decimal` (FR-008c, sérialisation string). | ✅ |
| P6 | Pivot Indicateur unique | N/A — la feature ne stocke aucune valeur ESG, elle rend des payloads. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Aucun nouveau rôle. `show_match_card.link` contraint à `^/` (chemin interne) — FR-008. | ✅ |
| P8 | Édition manuelle + sync LLM | Les payloads sont produits par le LLM ; pas de mutation introduite ici. | ✅ |
| P9 | Tool-use LLM fiable | 12 tools nommés en verbe (`show_*`), chacun avec `description` / `use_when` / `dont_use_when` / schéma Pydantic strict (`extra="forbid"`) / au moins un `positive_example`. | ✅ |
| P10 | UX bottom sheet | Les visualisations vivent INLINE dans la bulle LLM (par construction de F16) ; ce point est explicitement distinct du bottom sheet F15 réservé aux composants interactifs `ask_*`. Aucun composant `<Show*>` ne déclenche d'interaction qui devrait passer par le bottom sheet. | ✅ |

**Verdict** : tous les gates passent. Pas d'amendement constitutionnel requis.

### Contraintes techniques (rappel)

- Backend `.venv`, frontend `pnpm dev`, Postgres dockerisé.
- Hébergement Europe/AfO uniquement.
- Langue : français par défaut.
- Anti-XSS via `no_html` (F15) sur tout champ texte exposé.
- Chart.js / Leaflet / Mermaid chargés via `import()` dynamique côté frontend pour respecter le budget bundle initial < 500 KB.

## Project Structure

### Documentation (this feature)

```text
specs/016-tools-visualisation-inline/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── tools-visualisation.md   # Synthèse des 12 schémas Pydantic
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── orchestrator/
│       └── tools/                    # Réutilisation conventions F15
│           ├── __init__.py           # ÉTENDU : ajoute register_visualisation_tools()
│           ├── _common.py            # F15 — réutilisé sans modif
│           ├── _viz_common.py        # NOUVEAU : SourceRequiredMixin, AltTextMixin, helpers
│           ├── show_kpi_card.py      # NOUVEAU
│           ├── show_progress_bar.py  # NOUVEAU
│           ├── show_radar_chart.py   # NOUVEAU
│           ├── show_bar_chart.py     # NOUVEAU
│           ├── show_line_chart.py    # NOUVEAU
│           ├── show_pie_chart.py     # NOUVEAU
│           ├── show_donut_chart.py   # NOUVEAU
│           ├── show_timeline.py     # NOUVEAU
│           ├── show_comparison_table.py  # NOUVEAU
│           ├── show_match_card.py    # NOUVEAU
│           ├── show_map.py           # NOUVEAU [P2 — peut être DEFERRED]
│           ├── show_mermaid.py       # NOUVEAU [P2 — peut être DEFERRED]
│           └── mermaid_validator.py  # NOUVEAU [P2 — whitelist regex]
└── tests/
    └── tools/
        ├── test_show_kpi_card.py
        ├── test_show_progress_bar.py
        ├── test_show_radar_chart.py
        ├── test_show_bar_chart.py
        ├── test_show_line_chart.py
        ├── test_show_pie_chart.py
        ├── test_show_donut_chart.py
        ├── test_show_timeline.py
        ├── test_show_comparison_table.py
        ├── test_show_match_card.py
        ├── test_show_map.py            # P2
        ├── test_show_mermaid.py        # P2
        ├── test_mermaid_validator.py   # P2
        └── test_register_visualisation_tools.py

frontend/
├── app/
│   └── components/
│       └── chat/
│           ├── ChatMessageRenderer.vue   # ÉTENDU : switch payload.type pour les 12 tools
│           └── viz/                      # NOUVEAU dossier
│               ├── ShowKpiCard.vue
│               ├── ShowProgressBar.vue
│               ├── ShowRadarChart.vue
│               ├── ShowBarChart.vue
│               ├── ShowLineChart.vue
│               ├── ShowPieChart.vue
│               ├── ShowDonutChart.vue
│               ├── ShowTimeline.vue
│               ├── ShowComparisonTable.vue
│               ├── ShowMatchCard.vue
│               ├── ShowMap.vue        # [P2]
│               ├── ShowMermaid.vue    # [P2]
│               └── _useChartJs.ts     # composable lazy import chart.js
└── tests/
    └── components/viz/
        └── show-kpi-card.spec.ts (etc., snapshot + a11y) — best-effort
```

**Structure Decision** : monorepo backend/frontend existant (cf. F13/F14/F15). Le module `app/orchestrator/tools/` est **étendu** : ajout d'un nouveau registrar (`register_visualisation_tools()`) à `__init__.py`. Aucune modification de `tool_registry.py` (contrat F14). Frontend : nouveau sous-dossier `components/chat/viz/`.

## Complexity Tracking

Aucune violation. Pas de complexity tracking nécessaire.
