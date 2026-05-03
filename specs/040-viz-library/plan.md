# Implementation Plan: Visualization Library (UI de F16)

**Branch**: `040-viz-library` | **Date**: 2026-05-03 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/040-viz-library/spec.md`

## Summary

F40 livre la bibliothèque de composants `<Viz*>` que l'assistant LLM utilise pour afficher du contenu **display-only** dans les bulles : KPI cards, charts (line/area/bar/stacked/radar/gauge/pie/donut), tables typées virtualisées, diagrammes Mermaid sanitisés, mini-cartes Leaflet, plus le pin de source universel `<VizSourcePin>` qui matérialise P1 (sourcing). Aucune interaction modifiant l'état n'est admise dans une bulle (P10 — l'interaction passe par F39 bottom sheet engine).

Approche technique : 14 composants Vue 3 (Composition API) lazy-loaded, un composable `useChartTheme()` adossé aux tokens F36, un store Pinia `useSourcesStore()` (cache mémoire TTL 5 min, dédoublonnage des requêtes en vol), une route dev-only `/dev/viz-showcase` pour démonstration et tests visuels. Mermaid / Leaflet / chart.js sont encapsulés dans `<ClientOnly>` pour SSR-safety. Cible accessibilité **WCAG 2.1 AA** (clavier complet, `aria-label` synthétique + description longue alternative sur chaque chart, contraste ≥ 4.5:1) ; export CSV explicitement hors-scope MVP, reporté à F51.

## Technical Context

**Language/Version**: TypeScript 5.x + Vue 3.5 + Nuxt 4 (Composition API, `<script setup>`)
**Primary Dependencies (déjà installées dans `frontend/package.json`)** :
- chart.js `^4.4.7`
- mermaid `^11.4.1`
- leaflet `^1.9.4`
- vue-virtual-scroller `^2.0.0-beta.8`
- dompurify `^3.1.7`
- @floating-ui/vue `^1.1.6` (popover)
- pinia `^2.3.0` + @pinia/nuxt
- @heroicons/vue (icônes warning / source pin)
- axe-core `^4.10.2` (audit a11y dev / tests)

**Storage**: aucun — la feature est purement frontend display, pas de nouvelle table. La résolution des sources passe par un endpoint backend existant ou à compléter dans F03.

**Testing**:
- Unit + composant : Vitest + @vue/test-utils + happy-dom (déjà configurés)
- A11y : tests automatisés via axe-core sur `/dev/viz-showcase`
- Visuels : la route `/dev/viz-showcase` sert de fixture manuelle

**Target Platform**: Navigateurs evergreen (Chromium, Firefox, Safari, Edge) ; SSR Nuxt activé ; les composants lourds (chart.js, mermaid, leaflet) ne s'hydratent pas côté serveur.

**Project Type**: Web (frontend Nuxt 4 + backend FastAPI). Cette feature est strictement frontend ; le seul couplage backend est l'endpoint de résolution des sources, dépendance assumée de F03.

**Performance Goals**:
- LCP chart < 1 s sur 100 points (NFR-001 / SC-006)
- Hover sans frame > 16 ms (NFR-002 / SC-003)
- DataTable fluide à 1000 lignes (SC-003)
- Aucun chart / mermaid / leaflet dans le bundle initial (NFR-004 / SC-007)
- Popover source ouverte en < 300 ms p95 après clic (SC-002)

**Constraints**:
- Display-only strict — aucun `<input>`, `<button type="submit">`, ni primitive d'entrée dans une bulle (P10, FR-014, SC-008)
- Money typé `{amount, currency}`, jamais `float` (P5, FR-015, SC-009)
- `prefers-reduced-motion` désactive toutes les animations (FR-012)
- WCAG 2.1 AA respecté (FR-019, SC-011)
- SSR safety : `<ClientOnly>` autour de chart.js, mermaid, leaflet (FR-013)

**Scale/Scope**:
- ~14 composants Vue + 1 composable + 1 store + 1 route showcase
- Tables jusqu'à 1000+ lignes (virtualisation par défaut > 100)
- Cartes jusqu'à 50 pins clusterisés
- Charts ~100 points par défaut, 1000 acceptable

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle introduite par cette feature pointe-t-elle vers une `Source` `verified` ? Les nouveaux champs catalogue ont-ils `source_id NOT NULL` ? | ✅ — Le composant `<VizSourcePin>` est universel (FR-008) et tous les charts/KPI/cellules acceptent `source_id`. La feature ne stocke pas de données. |
| P2 | Multi-tenant RLS | Toute nouvelle table métier porte-t-elle `account_id` + politique RLS ? Les accès cross-tenant retournent-ils 404 ? | ✅ N/A — aucune nouvelle table. La résolution de sources passe par F03 (déjà conforme). |
| P3 | Audit log append-only | Toute mutation introduite est-elle journalisée avec `source_of_change` ? | ✅ N/A — feature display-only, aucune mutation. |
| P4 | Versioning + snapshot candidatures | Les nouveaux référentiels portent-ils `version`, `valid_from`, `valid_to` ? | ✅ — `<VizSourcePin>` affiche `valid_from` ; aucun nouveau référentiel introduit. |
| P5 | Money typé | Toute valeur monétaire utilise-t-elle `Money = {amount: Decimal, currency}` ? | ✅ — FR-006 (colonne `money`), FR-015 (interdiction `float`), SC-009 (audit). |
| P6 | Pivot Indicateur unique | Les données ESG sont-elles stockées comme valeurs d'`Indicateur` ? | ✅ N/A — feature display, ne stocke rien. Les charts radar E/S/G sont une vue, pas un stockage. |
| P7 | Plateforme fermée aux intermédiaires | La feature évite-t-elle tout rôle Intermédiaire/Bank/Fund ? | ✅ — composants display-only, aucun rôle introduit. |
| P8 | Édition manuelle + sync LLM | Tout champ alimenté par le LLM est-il modifiable manuellement ? | ✅ — la viz est purement display ; l'édition est gérée par F39 (bottom sheets). Le store sources écoute (futur) un événement de révocation pour invalider le cache (NFR P8). |
| P9 | Tool-use LLM fiable | Nouveaux tools : nom verbal, "use when", schéma strict, ≤ 10 tools ? | ✅ N/A — F40 est l'UI consommatrice ; les tools backend sont définis par F16. |
| P10 | UX bottom sheet | Les composants interactifs vivent-ils dans le bottom sheet ? | ✅ — FR-014 + SC-008 garantissent l'absence d'élément modifiant l'état dans les bulles ; toute interaction utilisateur reste dans F39. |

**Verdict** : ✅ tous gates `pass` ou `N/A`. Pas de violation à justifier dans `Complexity Tracking`.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter (interchangeable par env) ; embeddings Voyage `voyage-3.5` (1024 dim).
- Dev local : backend en `.venv`, Postgres seul service dockerisé, frontend en `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement (jamais USA).
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 dès le MVP.
- Langue : français par défaut ; anglais uniquement pour dossiers vers offres `accepted_languages = 'en'`.

## Project Structure

### Documentation (this feature)

```text
specs/040-viz-library/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (entités UI / store)
├── quickstart.md        # Phase 1 output (run + test rapide)
├── contracts/
│   └── sources-resolve.openapi.yaml    # contrat de l'endpoint de résolution
├── checklists/
│   └── requirements.md  # créé par /speckit-specify
└── tasks.md             # généré par /speckit-tasks
```

### Source Code (repository root)

```text
frontend/app/
├── components/
│   └── viz/
│       ├── VizKPICard.vue
│       ├── VizLineChart.vue
│       ├── VizAreaChart.vue
│       ├── VizBarChart.vue
│       ├── VizStackedBarChart.vue
│       ├── VizRadarChart.vue
│       ├── VizGaugeChart.vue
│       ├── VizPieChart.vue
│       ├── VizDonutChart.vue
│       ├── VizMermaidRenderer.vue
│       ├── VizDataTable.vue
│       ├── VizLeafletMap.vue
│       ├── VizSourcePin.vue
│       ├── VizEmptyState.vue
│       ├── VizLoadingState.vue
│       ├── index.ts            # exports lazy + types
│       └── __tests__/
│           ├── VizKPICard.test.ts
│           ├── VizSourcePin.test.ts
│           ├── VizDataTable.test.ts
│           ├── VizMermaidRenderer.test.ts
│           ├── VizLineChart.test.ts
│           ├── VizRadarChart.test.ts
│           ├── VizGaugeChart.test.ts
│           ├── VizLeafletMap.test.ts
│           └── a11y.showcase.test.ts   # axe-core sur /dev/viz-showcase
├── composables/
│   ├── useChartTheme.ts
│   └── __tests__/useChartTheme.test.ts
├── stores/
│   ├── sources.ts                      # useSourcesStore() (Pinia, TTL cache)
│   └── __tests__/sources.test.ts
├── types/
│   └── viz/
│       ├── chart.ts                    # ChartProps, VizSize, ColumnDef
│       └── source.ts                   # SourceRef, SourcePillar enum
├── utils/
│   ├── mermaidSanitize.ts              # wrapper DOMPurify autour mermaid SVG
│   ├── moneyFormat.ts                  # format Money = {amount, currency} → string
│   └── __tests__/
│       ├── mermaidSanitize.test.ts
│       └── moneyFormat.test.ts
└── pages/
    └── dev/
        └── viz-showcase.vue            # route dev-only (guarded NODE_ENV !== 'production')
```

**Structure Decision** : layout standard Nuxt 4 `app/`. Tous les composants sont regroupés sous `app/components/viz/` pour éviter toute confusion avec `app/components/chat/bottom-sheet/` (F39) ou les UI primitives (F37). Le composable, le store et les types sont colocalisés selon les conventions existantes (`app/composables/`, `app/stores/`, `app/types/`). La route showcase est sous `pages/dev/` pour bénéficier du guard environnement déjà en place sur ce préfixe.

## Complexity Tracking

> Aucune violation constitutionnelle — section laissée vide.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (aucune) | — | — |
