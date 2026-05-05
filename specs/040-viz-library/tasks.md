# Tasks: Visualization Library (UI de F16)

**Feature** : `040-viz-library`
**Spec** : [`spec.md`](./spec.md) — **Plan** : [`plan.md`](./plan.md) — **Date** : 2026-05-03

Tests requis (par convention projet : couverture 80 % imposée par la constitution + cible WCAG 2.1 AA — clarif Q1). Les tasks de tests sont donc **incluses** dans chaque US.

Tous les chemins sont relatifs à la racine du repo `/Users/mac/Documents/projets/2025/esg_mefali_v2/`.

---

## Phase 1 — Setup (préalables transverses)

- [X] T001 Créer le squelette de répertoires de la feature : `frontend/app/components/viz/`, `frontend/app/components/viz/__tests__/`, `frontend/app/types/viz/`, `frontend/app/pages/dev/`, `frontend/app/utils/__tests__/fixtures/viz/`.
- [X] T002 [P] Vérifier la présence des dépendances `chart.js@^4.4.7`, `mermaid@^11.4.1`, `leaflet@^1.9.4`, `vue-virtual-scroller@^2.0.0-beta.8`, `dompurify@^3.1.7`, `@floating-ui/vue@^1.1.6`, `axe-core@^4.10.2` dans `frontend/package.json` (déjà présentes — task de validation, pas d'install).
- [X] T003 [P] Ajouter les types CSS pour leaflet : importer `leaflet/dist/leaflet.css` dans `frontend/app/assets/css/leaflet.css` et le référencer depuis `nuxt.config.ts` `css: []`.

---

## Phase 2 — Foundational (bloquant pour toutes les US)

**Goal** : poser les types partagés, le store de sources, le composable de thème et les utilitaires consommés par tous les composants `<Viz*>`.

- [X] T004 [P] Créer les types `SourcePillar`, `SourceStatus`, `SourceRef` dans `frontend/app/types/viz/source.ts` selon `data-model.md §1.1`.
- [X] T005 [P] Créer les types `MoneyValue`, `VizSize`, `BaseChartProps`, `ColumnType`, `ColumnDef`, `DataTableProps`, `MapPin`, `MermaidPayload` dans `frontend/app/types/viz/chart.ts` selon `data-model.md §1.2–1.6`.
- [X] T006 [P] Implémenter `frontend/app/utils/moneyFormat.ts` exposant `formatMoney(value: MoneyValue, locale='fr-FR'): string` via `Intl.NumberFormat` (sans jamais convertir `amount` en `number`). Réf. R8.
- [X] T007 [P] Test : `frontend/app/utils/__tests__/moneyFormat.test.ts` — couvre XOF / EUR / USD, montants entiers et décimaux, locale `fr-FR`, vérifie qu'aucun `Number(amount)` n'est appelé (espionnage `Number`).
- [X] T008 [P] Implémenter `frontend/app/utils/mermaidSanitize.ts` exposant `sanitizeMermaidSvg(svg: string): string` via DOMPurify avec `USE_PROFILES: { svg: true, svgFilters: true }`. Réf. R2.
- [X] T009 [P] Test : `frontend/app/utils/__tests__/mermaidSanitize.test.ts` — vérifie suppression de `<script>`, des handlers `on*`, des URI `javascript:` et conservation de `<title>` / `<desc>` pour a11y.
- [X] T010 Implémenter le store `useSourcesStore()` dans `frontend/app/stores/sources.ts` avec `cache: Map`, `inFlight: Map`, méthodes `resolve / peek / invalidate / reset` et constante exportée `SOURCES_TTL_MS = 5 * 60 * 1000`. Réf. R3 + `data-model.md §2`.
- [X] T011 Test : `frontend/app/stores/__tests__/sources.test.ts` — TTL fresh hit, expiration, dédoublonnage `inFlight`, propagation 404 (`SourceNotFoundError`), invalidate ciblé / total. Utilise `vi.useFakeTimers()`.
- [X] T012 [P] Implémenter `useChartTheme()` dans `frontend/app/composables/useChartTheme.ts` lisant les CSS variables F36 + `prefers-reduced-motion`. Réf. R5 + `data-model.md §3`.
- [X] T013 [P] Test : `frontend/app/composables/__tests__/useChartTheme.test.ts` — vérifie lecture CSS variables, basculement `reducedMotion` quand `matchMedia` retourne `matches=true`.
- [X] T014 Créer `frontend/app/components/viz/index.ts` qui exporte tous les composants `<Viz*>` en lazy via `defineAsyncComponent(() => import(...))` ainsi que les types depuis `types/viz/`. Réf. R1.

---

## Phase 3 — US5 (P1) Source pin universel

**Goal** : `<VizSourcePin>` fonctionnel avant tous les autres composants qui le réutilisent.

**Independent Test** : monter `<VizSourcePin source_id="src_abc">` ; cliquer ouvre la popover qui affiche `{title, url, pillar, valid_from}` du store mocké ; cas `revoked` affiche icône warning ; `source_id` introuvable → composant invisible.

- [X] T015 [US5] Implémenter `frontend/app/components/viz/VizSourcePin.vue` : `<button>` natif `aria-haspopup="dialog"`, `aria-expanded`, focus visible, ouverture popover via `@floating-ui/vue` ; au clic appelle `useSourcesStore().resolve(source_id)` ; gère états `loading / success / not-found / revoked`. Fail-silent quand `resolve` rejette en 404.
- [X] T016 [US5] Implémenter le rendu du contenu popover (titre, URL `target="_blank" rel="noopener noreferrer"`, badge `pillar` coloré selon enum, `valid_from`, message `revoked_reason` quand `status='revoked'`).
- [X] T017 [P] [US5] Test : `frontend/app/components/viz/__tests__/VizSourcePin.test.ts` — couvre : pin rendu pour `verified`, popover contenu correct, clic clavier (Enter/Space), `revoked` affiche warning, 404 → composant absent du DOM, valeur `pillar` hors enum → fallback neutre + console.error.

---

## Phase 4 — US1 (P1) KPICard avec source pin

**Goal** : `<VizKPICard>` rendant valeur `tabular-nums`, delta coloré, unit, et pin source réutilisé.

**Independent Test** : KPI `{label: "Score E", value: 72, unit: "/100", delta: +5, source_id: "src_abc"}` rend valeur tabular-nums, delta vert flèche montante, pin cliquable ouvre popover.

- [X] T018 [US1] Implémenter `frontend/app/components/viz/VizKPICard.vue` avec props `{label, value, unit?, delta?, deltaUnit?, source_id?, size, loading, empty, ariaLabel?, longDescription?}`. 3 tailles `sm/md/lg`. Valeur en `tabular-nums`. Delta : flèche `↑` vert / `↓` rouge / `=` neutre, doublé d'un signe `+/-` (a11y daltonisme).
- [X] T019 [US1] Intégrer `<VizSourcePin>` quand `source_id` fourni ; intégrer `<VizLoadingState>` (skeleton) et `<VizEmptyState>` quand `loading`/`empty`. `aria-label` synthétique auto-généré, `longDescription` exposée via `<span class="sr-only">`.
- [X] T020 [P] [US1] Test : `frontend/app/components/viz/__tests__/VizKPICard.test.ts` — props rendues, classes `tabular-nums`, delta couleur+signe, absence de pin sans `source_id`, états `loading`/`empty` prioritaires sur le rendu, attributs ARIA présents.

---

## Phase 5 — Foundational UI states (consommés par toutes les US suivantes)

- [X] T021 [P] Implémenter `frontend/app/components/viz/VizLoadingState.vue` (skeleton shimmer, respect `prefers-reduced-motion`).
- [X] T022 [P] Implémenter `frontend/app/components/viz/VizEmptyState.vue` (illustration sobre + message FR par défaut configurable via prop `message?`).

---

## Phase 6 — US2 (P1) Charts standards

**Goal** : Line, Area, Bar, StackedBar, Radar, Pie, Donut — tous lazy-loaded, theme partagé, états `loading`/`empty`, source_id.

**Independent Test** : `/dev/viz-showcase` rend chaque type avec mock data sans erreur ; toggle manuel `loading`/`empty` fonctionne.

- [X] T023 [P] [US2] Implémenter `frontend/app/components/viz/VizLineChart.vue` — chart.js `line` + gradient, dynamic import dans `<ClientOnly>`, theme via `useChartTheme()`, props `BaseChartProps & { series: Array<{label,points:{x,y}[]}> }`. `role="img"` + `aria-label` + `<span class="sr-only">` description longue auto.
- [X] T024 [P] [US2] Implémenter `frontend/app/components/viz/VizAreaChart.vue` — variante de LineChart `fill: 'origin'`.
- [X] T025 [P] [US2] Implémenter `frontend/app/components/viz/VizBarChart.vue` — chart.js `bar`, animation `growUp` 320 ms désactivée si `reducedMotion`.
- [X] T026 [P] [US2] Implémenter `frontend/app/components/viz/VizStackedBarChart.vue` — `stacked: true` sur axes.
- [X] T027 [P] [US2] Implémenter `frontend/app/components/viz/VizRadarChart.vue` — `radar` chart.js, max 6 points (warning console au-delà), filled subtle.
- [X] T028 [P] [US2] Implémenter `frontend/app/components/viz/VizPieChart.vue` — `pie` chart.js.
- [X] T029 [P] [US2] Implémenter `frontend/app/components/viz/VizDonutChart.vue` — `doughnut` chart.js, `cutout: '60%'`.
- [X] T030 [P] [US2] Test : `frontend/app/components/viz/__tests__/VizLineChart.test.ts` — montage SSR-safe (ClientOnly), prop `loading` masque le canvas, prop `empty` affiche EmptyState, `aria-label` présent.
- [X] T031 [P] [US2] Test : `frontend/app/components/viz/__tests__/VizRadarChart.test.ts` — vérifie warning au-delà de 6 points, max conservé.
- [X] T032 [P] [US2] Test mutualisé : `frontend/app/components/viz/__tests__/charts-common.test.ts` — boucle sur Bar/StackedBar/Pie/Donut/Area : props rendues, theme appliqué, `prefers-reduced-motion` désactive l'animation.

---

## Phase 7 — US3 (P1) MermaidRenderer avec fallback

**Goal** : SVG sanitisé + fallback texte sans crash.

**Independent Test** : sur `/dev/viz-showcase`, script valide rend SVG ; script invalide rend `<pre>` avec source brut, sans erreur dans la conversation parente.

- [X] T033 [US3] Implémenter `frontend/app/components/viz/VizMermaidRenderer.vue` : import dynamique `mermaid` dans `<ClientOnly>`, appelle `mermaid.render(diagramId, script)` puis `sanitizeMermaidSvg()`, injecte via `v-html`. Try/catch → fallback `<pre><code class="language-mermaid">{{script}}</code></pre>`. Ajoute `<title>` et `<desc>` ARIA dans le SVG sanitisé.
- [X] T034 [P] [US3] Test : `frontend/app/components/viz/__tests__/VizMermaidRenderer.test.ts` — script valide → SVG sanitisé sans `<script>`, script invalide → fallback texte présent et pas d'exception propagée, SSR : aucun appel à `document` côté serveur.

---

## Phase 8 — US4 (P1) DataTable virtualisée

**Goal** : table typée, virtualisée > 100 lignes, pagination optionnelle, formatage `money` strict.

**Independent Test** : 1000 lignes scrollées sans lag ; tri colonne `money` ; recherche full-text ; mode paginé via prop.

- [X] T035 [US4] Implémenter `frontend/app/components/viz/VizDataTable.vue` : props `DataTableProps`, rendu basé sur `RecycleScroller` (`vue-virtual-scroller`) quand `rows.length > 100 && !paginate`, sinon table standard. Tri par colonne (asc/desc), recherche full-text sur colonnes `searchable`. Cellule `type='money'` : appelle `formatMoney` ; cellule `type='badge'` : badge stylé ; cellule `type='date'` : `Intl.DateTimeFormat`.
- [X] T036 [US4] Garantir l'ARIA : `<table role="table">`, `<th scope="col">` par colonne, `aria-sort` sur la colonne triée, `aria-label` global, message live (`role="status"`) quand recherche/tri change le nombre de lignes affichées.
- [X] T037 [US4] Brancher `<VizSourcePin>` au niveau cellule via slot scopé optionnel `<template #cell-source="{ row }">` ; quand un row porte un `source_id`, le slot par défaut affiche le pin.
- [X] T038 [P] [US4] Test : `frontend/app/components/viz/__tests__/VizDataTable.test.ts` — 1000 lignes virtualisées (vérifie nombre de DOM nodes < seuil), tri money cohérent, recherche filtre, mode `paginate: { pageSize: 25 }` désactive virtualisation, money number brut → warning console + cellule `--`.

---

## Phase 9 — US6 (P2) GaugeChart

**Goal** : score 0–100, arc 270°, valeur centrale, zones colorées avec doublure non-couleur.

**Independent Test** : `<VizGaugeChart :value="68">` rend aiguille en zone orange ; `prefers-reduced-motion` désactive l'animation d'entrée.

- [X] T039 [US6] Implémenter `frontend/app/components/viz/VizGaugeChart.vue` — basé sur chart.js `doughnut` configuré arc 270°, plugin custom pour aiguille + valeur centrale ; zones rouge/orange/vert (≤33 / 34-66 / ≥67) avec icône doublure (a11y daltonisme).
- [X] T040 [P] [US6] Test : `frontend/app/components/viz/__tests__/VizGaugeChart.test.ts` — valeur 68 → zone orange, valeur 90 → vert, valeur 12 → rouge, animation entrée désactivée si `reducedMotion`.

---

## Phase 10 — US7 (P2) LeafletMap

**Goal** : 50 pins clusterisés, zoom max 5, attribution OSM.

**Independent Test** : `<VizLeafletMap :pins="50pins">` rend clusters et plafonne le zoom.

- [X] T041 [US7] Implémenter `frontend/app/components/viz/VizLeafletMap.vue` — import dynamique `leaflet` dans `<ClientOnly>`, tile OSM standard avec attribution, `maxZoom: 5`, plugin `leaflet.markercluster` chargé en lazy. Pins typés `MapPin[]`. `aria-label` global.
- [X] T042 [P] [US7] Test : `frontend/app/components/viz/__tests__/VizLeafletMap.test.ts` — 50 pins clusterisés (mock clustering), `maxZoom` respecté, attribution présente, no SSR call.

---

## Phase 11 — Showcase + a11y harness

**Goal** : route dev-only rendant tous les composants + audit axe-core automatisé.

- [X] T043 Créer `frontend/app/pages/dev/viz-showcase.vue` : guard `process.dev` (sinon `throw createError({ statusCode: 404 })`), import des fixtures, rendu des 14 composants avec toggles `loading`/`empty` et boutons de bascule `paginate` pour la table.
- [X] T044 [P] Créer fixtures partagées `frontend/app/utils/__tests__/fixtures/viz/index.ts` (KPI sample, séries chart, data table 12 et 1000 lignes, mermaid valide+invalide, 50 pins, scénarios revoked/not-found pour les sources).
- [X] T045 Test a11y : `frontend/app/components/viz/__tests__/a11y.showcase.test.ts` — monte la showcase, exécute `axe-core` (règles WCAG 2.1 AA), assertion : aucune violation `serious` ou `critical`. Échoue le build si violation détectée. Réf. SC-011.
- [X] T046 Test invariants statiques : `frontend/app/components/viz/__tests__/invariants.test.ts` — scanne le contenu des fichiers `app/components/viz/*.vue` (lecture fs en test) pour vérifier I1 (aucun `<input>`, `<button type="submit">`, `v-model` exposé) et I2 (aucun littéral `amount: <number>`). Échec si violation. Réf. SC-008 / SC-009.

---

## Phase 12 — Polish & cross-cutting

- [X] T047 [P] Mettre à jour `frontend/app/utils/sanitize.ts` (s'il existe déjà) pour réexporter `sanitizeMermaidSvg` (single source of truth des appels DOMPurify côté front).
- [X] T048 [P] Vérifier le bundle : exécuter `pnpm build` depuis `frontend/`, inspecter `dist/_nuxt/` et confirmer que chart.js / mermaid / leaflet sont des chunks asynchrones séparés (SC-007). Documenter la commande de vérification dans `quickstart.md` §7 (déjà présente — task de vérification).
- [X] T049 [P] Ajouter un guard runtime dans `frontend/app/components/viz/index.ts` qui log un warning console.dev si un composant `<Viz*>` est monté à l'intérieur d'un slot bottom sheet (heuristique : `provide/inject` `__BOTTOM_SHEET_CTX__` créé par F39). Tolérant : warning seulement, pas d'erreur. Réf. P10.
- [X] T050 [P] Lancer `pnpm vitest run` complet et vérifier la couverture des fichiers `app/components/viz`, `app/composables/useChartTheme`, `app/stores/sources`, `app/utils/moneyFormat`, `app/utils/mermaidSanitize` ≥ 80 %.
- [X] T051 Documenter la feature dans le README frontend (section "Visualization Library — F40") : liste des composants, routes dev, conventions a11y, dépendance F03 pour les sources.

---

## Dependencies (ordre de complétion des stories)

```
Phase 1 (Setup T001-T003)
        │
        ▼
Phase 2 (Foundational T004-T014) ── BLOQUANT pour toutes les US
        │
        ▼
Phase 3 (US5 — VizSourcePin) ── BLOQUANT pour US1, US2 (charts avec source_id), US4 (cellules avec source)
        │
        ├─► Phase 5 (UI states T021-T022) ── BLOQUANT pour US1/US2/US4/US6/US7
        │
        ▼
Phase 4 (US1 — KPICard)              ◄── MVP
        │
        ▼
Phase 6 (US2 — Charts standards)
        │
        ▼
Phase 7 (US3 — Mermaid)              indépendante de US2/US4 après Phase 5
        │
        ▼
Phase 8 (US4 — DataTable)            indépendante de US2/US3/US6/US7
        │
        ▼
Phase 9 (US6 — Gauge)                P2 — indépendante
        │
        ▼
Phase 10 (US7 — LeafletMap)          P2 — indépendante
        │
        ▼
Phase 11 (Showcase + a11y harness)   nécessite TOUTES les US implémentées
        │
        ▼
Phase 12 (Polish)
```

**Règle clé** : US1, US2, US3, US4 (toutes P1) deviennent indépendantes une fois Phase 2 + Phase 3 (US5) + Phase 5 livrées. US6 et US7 (P2) peuvent être parallélisées avec n'importe laquelle des P1.

---

## Parallel execution examples

**Phase 2 (Foundational)** — après T004 :

```
T005 [P] (types chart) || T006 [P] (moneyFormat) || T008 [P] (mermaidSanitize) || T012 [P] (useChartTheme)
puis
T007 [P] || T009 [P] || T013 [P] (tests des utilitaires)
puis T010 → T011 (store + test, séquentiels même fichier d'index)
```

**Phase 6 (US2 — charts standards)** — après Phase 5 :

```
T023 [P] || T024 [P] || T025 [P] || T026 [P] || T027 [P] || T028 [P] || T029 [P]
puis
T030 [P] || T031 [P] || T032 [P]
```

**Phase 11 (Showcase + a11y)** :

```
T044 [P] (fixtures)
puis T043 (page) qui dépend des fixtures
puis T045 (a11y harness) qui dépend de T043
en parallèle T046 (invariants statiques) — indépendant
```

---

## Implementation strategy

### MVP minimal (livraison incrémentale n°1)

Phases 1 → 2 → 3 (US5) → 5 → **4 (US1)** + Phase 11 réduite (showcase ne rend que `<VizSourcePin>` + `<VizKPICard>`) + Phase 12 (T050 couverture, T046 invariants).
→ Permet à l'assistant LLM de répondre avec des KPI sourcés conformes P1, sans bloquer l'arrivée des autres composants.

### Livraison n°2

Ajouter Phases 6 (US2 — charts) + 7 (US3 — mermaid) + 8 (US4 — DataTable) en parallèle entre 3 développeurs.

### Livraison n°3

Phases 9 (US6) + 10 (US7) + Phase 11 complète (a11y harness sur showcase complète) + Phase 12 finalisée.

---

## Independent test criteria (synthèse spec.md)

| US | Critère d'acceptation principal |
|----|----------------------------------|
| US5 | `<VizSourcePin>` cliquable ouvre popover avec données réelles (`title, url, pillar, valid_from`). |
| US1 | `<VizKPICard>` rend valeur tabular-nums, delta vert/rouge avec signe, pin source si `source_id`. |
| US2 | Line/Area/Bar/Stacked/Radar/Pie/Donut s'affichent sur showcase sans erreur, `loading`/`empty` fonctionnels. |
| US3 | Mermaid valide → SVG sanitisé ; invalide → fallback texte sans crash. |
| US4 | DataTable rend 1000 lignes fluides, colonne money formatée `Intl`, mode paginé activable. |
| US6 | Gauge 68 → zone orange, animation désactivée si `reducedMotion`. |
| US7 | LeafletMap 50 pins clusterisés, zoom max 5, attribution OSM. |

---

## Format validation

Toutes les tasks T001–T051 respectent le format `- [ ] T### [P?] [US?] Description avec chemin de fichier`.
- Setup (T001-T003) : pas de label US.
- Foundational (T004-T014) : pas de label US.
- US5 (T015-T017), US1 (T018-T020), US2 (T023-T032), US3 (T033-T034), US4 (T035-T038), US6 (T039-T040), US7 (T041-T042) : label US présent.
- Phase 5 / 11 / 12 (cross-cutting) : pas de label US.
