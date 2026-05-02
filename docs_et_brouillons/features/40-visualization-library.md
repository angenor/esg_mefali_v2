# F40 — Visualization Library (UI de F16)

**Phase** : B — Briques transversales LLM/chat
**Modules brainstorm** : 1.1.2 — bulles LLM **display-only** (KPI, charts, mermaid, tables, map)
**Dépendances** : F36, F37, F16 (backend tools de viz), F03 (sourcing)
**Estimation** : 4 jours

## Contexte et objectif

Concrétise **P10 / P1** : bulles LLM affichent du contenu **non-interactif** (texte, KPI, charts, mermaid, tables, mini-cartes). Chaque visualisation peut afficher son **`source_id` cliquable** (P1) ouvrant une `<UiPopover>` avec titre + URL + pillar source.

Lib charts : **chart.js** (F01), **mermaid**, **Leaflet** mini-cartes, **vue-virtual-scroller** grands tableaux.

## User Stories

- **US1 KPICard (P1)** — `<VizKPICard>` : valeur tabular-nums, label, delta optionnel (↑/↓ + couleur), unit, source pin. 3 tailles.
- **US2 LineChart / AreaChart (P1)** — séries multiples, axe temps, tooltip hover, gradient subtil, légende sobre.
- **US3 BarChart / StackedBar (P1)** — vertical/horizontal, animation `growUp` 320 ms.
- **US4 RadarChart (P1)** — scoring ESG 3 axes E/S/G ou multi-référentiels. Filled subtle, max 6 points.
- **US5 GaugeChart (P2)** — credit_score 0-100, arc 270°, valeur centrale, zones colorées.
- **US6 PieChart / Donut (P1)** — usage parcimonieux (carbone Scope 1/2/3 décomposition).
- **US7 MermaidRenderer (P1)** — wrapper `mermaid` lazy import, fallback texte si parsing fail, sanitize SVG.
- **US8 DataTable (P1)** — colonnes typées (texte, number, date, badge, money), tri, recherche, pagination, virtualisation > 100 lignes. Empty state. Export CSV (P2).
- **US9 LeafletMap (P2)** — mini-carte intermédiaires F25, pins + clusters, zoom max 5, attribution OSM.
- **US10 SourcePin (P1)** — `<VizSourcePin>` icône `(source)` superscript brand-500 ; click → popover `{title, url, pillar, valid_from}`. Réutilisé partout.
- **US11 EmptyState chart (P1)** — illustration sobre + "Aucune donnée disponible — lancez un calcul ESG".
- **US12 LoadingState chart (P1)** — skeleton chart shimmer ; jamais le chart vide visible avant data.

## Exigences fonctionnelles

- **FR-001** : `frontend/app/components/viz/Viz<Name>.vue`.
- **FR-002** : Wrapper chart.js avec config par défaut (couleurs F36, fonts Inter, tooltip cohérent).
- **FR-003** : Composable `useChartTheme()` expose colors, fonts, tooltips standardisés.
- **FR-004** : Mermaid + chart.js lazy-loaded (dynamic import) — pas dans bundle initial.
- **FR-005** : Charts acceptent `:title, :caption, :source_id?, :size, :loading, :empty`.
- **FR-006** : Tableaux : `:rows, :columns: [{key, label, type, format?}]`. Aucun fetch interne.
- **FR-007** : Sanitize Mermaid SVG (DOMPurify) — XSS-proof.

## Exigences non-fonctionnelles

- **NFR-001** : LCP chart < 1 s sur 100 points.
- **NFR-002** : Hover ne bloque pas main thread (frame < 16 ms).
- **NFR-003** : `prefers-reduced-motion` désactive animations chart.
- **NFR-004** : mermaid + leaflet + chart.js en async chunks.

## Success Criteria

- **SC-001** : `/dev/viz-showcase` rend chaque type avec mock data sans erreur.
- **SC-002** : `<VizSourcePin>` cliqué → popover source réelle DB.
- **SC-003** : DataTable rend 1000 lignes sans lag.
- **SC-004** : Mermaid invalide → fallback texte sans crash.
- **SC-005** : LeafletMap rend 50 pins clustérisés.

## Hors-scope MVP

- Charts D3 custom (heatmap, sankey, treemap) → post-MVP.
- Export PNG/SVG → P2 (utile rapports F51).
- Animations avancées (morphing) → post-MVP.

## Risques et points de vigilance

- chart.js v4 : verrouiller version `package.json`.
- Mermaid SSR : `<ClientOnly>` wrapper, pas d'hydratation SSR.
- Source révoquée (`status='revoked'`) : icône warning (cohérent F03 P1).
- Daltoniens : tester Color Oracle, éviter rouge/vert seuls.
