# Phase 0 — Research

**Feature** : 040-viz-library
**Date** : 2026-05-03

Aucun marqueur `NEEDS CLARIFICATION` dans `plan.md` (la phase `/speckit-clarify` a fermé les 5 ambiguïtés majeures). Cette note documente les décisions techniques retenues, leurs alternatives rejetées et les ressources de référence à consulter pendant `/speckit-tasks` et `/speckit-implement`.

---

## R1 — Lazy-loading des libs lourdes (chart.js / mermaid / leaflet)

**Decision** : importer chart.js, mermaid et leaflet via `import()` dynamique à l'intérieur du `<script setup>` de chaque composant `<Viz*>` qui les consomme, encapsulé dans `<ClientOnly>`.

**Rationale** :
- NFR-004 / SC-007 imposent l'absence de ces libs dans le bundle initial.
- Nuxt 4 + Vite produit automatiquement un chunk asynchrone pour chaque `import()` dynamique.
- `<ClientOnly>` empêche l'évaluation côté serveur (mermaid et leaflet manipulent `window`/`document`).

**Alternatives rejetées** :
- `defineAsyncComponent` au niveau de `index.ts` : moins lisible et rend impossible le ciblage fin d'erreurs par composant.
- Plugin Nuxt global qui charge les libs au boot : casse le lazy-loading, alourdit le bundle initial.

**Ressources** : Nuxt 4 docs `<ClientOnly>` ; chart.js v4 tree-shaking guide ; mermaid v11 ESM API.

---

## R2 — Sanitization du SVG Mermaid

**Decision** : pipeline `mermaid.render() → DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true } }) → injection via `v-html`. En cas d'exception de parsing mermaid, fallback `<pre><code class="language-mermaid">...</code></pre>` montrant le script source.

**Rationale** :
- FR-007 + SC-004 : le SVG doit être XSS-proof et le composant ne doit jamais crasher.
- DOMPurify est déjà installé (`^3.1.7`) et utilisé dans `frontend/app/utils/sanitize.ts`.
- Le profil SVG de DOMPurify retire `<script>`, `on*` handlers, `xlink:href` douteux, `javascript:` URIs.

**Alternatives rejetées** :
- Utiliser le `securityLevel: 'strict'` de mermaid sans DOMPurify : insuffisant historiquement (CVE-2021-43840 et suivants).
- Ne pas afficher de fallback : viole SC-004.

**Ressources** : DOMPurify SVG profile docs ; mermaid v11 changelog (sécurité) ; CVE list Mermaid 2023-2025.

---

## R3 — Store Pinia `useSourcesStore()` (cache TTL + dédoublonnage)

**Decision** : un store Pinia avec :
- `cache: Map<source_id, { data: SourceRef, fetchedAt: number }>`
- `inFlight: Map<source_id, Promise<SourceRef>>`
- méthode `resolve(source_id): Promise<SourceRef>` :
  1. Si entry frais (≤ 5 min), retourne immédiatement.
  2. Sinon si déjà en vol, retourne la promesse en vol (dédoublonnage).
  3. Sinon `fetch('/api/sources/:id')` ; en succès stocke + supprime `inFlight`.
- `invalidate(source_id?)` exposée pour permettre une future écoute SSE `source_revoked` (P8).

**Rationale** :
- Q2 de `/speckit-clarify` a tranché : cache mémoire TTL ~5 min, dédoublonnage.
- Permet plusieurs `<VizSourcePin>` simultanés sur la même page sans burst d'appels.
- L'API `invalidate` prépare l'intégration future avec le bus d'événements (sortie de scope MVP mais prévue).

**Alternatives rejetées** :
- IndexedDB : sur-dimensionné et casse l'invalidation rapide attendue côté MVP.
- Préchargement bulk au montage de la conversation : forcerait un endpoint `POST /sources/resolve` qui n'existe pas et complexifie le couplage UI/conversation.
- Cache HTTP côté serveur uniquement : ne dédoublonne pas les appels concurrents en vol côté client.

**Ressources** : Pinia setup stores ; Nuxt 4 `useFetch` vs `$fetch` (préférer `$fetch` côté store pour contrôler le cache).

---

## R4 — Virtualisation `<VizDataTable>` au-delà de 100 lignes

**Decision** : utiliser `vue-virtual-scroller` (`RecycleScroller`) en mode liste verticale dès que `rows.length > 100`. Quand la prop `paginate?: { pageSize }` est fournie, basculer en mode paginé classique (rendu page par page sans virtualisation interne).

**Rationale** :
- Q4 de `/speckit-clarify` a tranché : virtualisation par défaut > 100, pagination optionnelle.
- `vue-virtual-scroller` est déjà installé et est la référence Vue 3 pour ce besoin.
- Le seuil 100 évite la complexité virtualisation pour les tables courtes (la majorité des cas LLM).

**Alternatives rejetées** :
- `@tanstack/vue-virtual` : nécessite un layout sur-mesure pour tables ; vue-virtual-scroller offre `RecycleScroller` prêt à l'emploi.
- Virtualisation systématique : surcoût inutile sur 5-20 lignes, complexité de tests.
- Pagination uniquement : viole SC-003 (1000 lignes fluides en scroll continu attendu).

**Ressources** : vue-virtual-scroller `RecycleScroller` docs ; benchmarks tables Vue 3.

---

## R5 — Theme partagé charts via `useChartTheme()`

**Decision** : composable `useChartTheme()` retourne un objet immuable `{ palette, fonts, tooltip, animations, gridColors, axisColors }` lu à partir des CSS variables exposées par F36 (design tokens). Les charts consomment ce thème pour configurer chart.js (via `Chart.defaults` mergé localement) et Leaflet (`tile.attribution`, layer styles).

**Rationale** :
- FR-002 / FR-004 demandent une cohérence visuelle.
- Lire les CSS variables (`getComputedStyle(document.documentElement).getPropertyValue('--brand-500')`) garantit le suivi automatique d'un changement de thème (light/dark futur).
- Évite la duplication des couleurs entre design system F36 et chart.js.

**Alternatives rejetées** :
- Hardcoder les couleurs dans chaque composant : viole FR-002.
- Exporter une constante TS partagée sans lecture CSS : casse le couplage avec F36 (recompilation requise pour tout changement de palette).

**Ressources** : F36 spec ; chart.js v4 `Chart.defaults` ; CSS Custom Properties JS API.

---

## R6 — Accessibilité WCAG 2.1 AA (charts non-textuels)

**Decision** : chaque composant chart expose :
- `aria-label` synthétique généré à partir de `title + caption + valeur clé`
- Description longue alternative dans un `<div class="sr-only">` ou via `aria-describedby` pointant un texte lisible décrivant les données (titre, légende, points de données majeurs)
- `role="img"` sur le canvas / SVG

`<VizSourcePin>` est implémenté comme `<button>` natif (focus, Enter / Space) avec `aria-haspopup="dialog"` et `aria-expanded`. La popover utilise `@floating-ui/vue` avec gestion focus trap. axe-core est exécuté en test sur `/dev/viz-showcase` via `vitest` + `@axe-core/playwright` (ou `axe-core` direct sur le DOM happy-dom pour tests rapides).

**Rationale** :
- Q1 de `/speckit-clarify` a tranché : WCAG 2.1 AA.
- chart.js peint sur `<canvas>` qui n'est pas accessible nativement ; le pattern `role="img"` + description longue est le contournement standard recommandé par chart.js.
- Mermaid produit du SVG accessible si on injecte `<title>` et `<desc>` après sanitization (DOMPurify les conserve).

**Alternatives rejetées** :
- Convertir les charts canvas en SVG (chart.js → autre lib) : refonte technique disproportionnée.
- Pas de cible WCAG : exclu par Q1.

**Ressources** : chart.js a11y guide ; axe-core API ; W3C ARIA Authoring Practices Guide (graphics).

---

## R7 — Dépendance backend : endpoint de résolution des sources

**Decision** : assumer l'existence d'un endpoint `GET /api/sources/{id}` retournant `SourceRef` (cf. `contracts/sources-resolve.openapi.yaml`). Si l'endpoint n'existe pas encore au moment de l'implémentation F40, le store `useSourcesStore` accepte un mock injectable (config dev) et la PR de F40 inclut une issue pour finaliser l'endpoint dans F03.

**Rationale** :
- F40 est UI ; couplage minimal avec backend.
- F03 (sourcing) est dépendance déclarée.
- Un mock injectable permet de tester `<VizSourcePin>` indépendamment du backend.

**Alternatives rejetées** :
- Bloquer F40 sur F03 : casse la planification (F36/F37 déjà OK, F40 vise la chaîne UI complète).
- Implémenter l'endpoint dans F40 : viole le découpage feature (l'endpoint appartient à F03).

**Ressources** : OpenAPI 3.1 spec ; FastAPI router patterns existants.

---

## R8 — Money formatting

**Decision** : utilitaire `frontend/app/utils/moneyFormat.ts` qui prend `{ amount: string | Decimal, currency: ISO4217 }` et retourne une string formatée via `Intl.NumberFormat('fr-FR', { style: 'currency', currency })`. Le type d'`amount` est `string` côté frontend (sérialisation Decimal côté backend) ; jamais `number`.

**Rationale** :
- P5 + FR-015 + SC-009 : interdiction stricte de `float`.
- Sérialisation Decimal côté Pydantic v2 → JSON `string` est le pattern projet.
- `Intl.NumberFormat` gère naturellement FCFA (XOF), EUR, USD.

**Alternatives rejetées** :
- `Number(amount).toFixed(2)` : convertit en `float`, viole P5.
- Lib externe (currency.js) : redondant avec `Intl`.

**Ressources** : ECMAScript `Intl.NumberFormat` ; ISO 4217 ; backend `MoneyValue` schema.

---

## R9 — Test strategy (unit + a11y + visual)

**Decision** :
- **Unit / composant** : Vitest + @vue/test-utils sur chaque composant (props rendus, état loading/empty, sanitization, formatage money).
- **Store** : tests Pinia setup-store sur cache TTL + dédoublonnage avec `vi.useFakeTimers()`.
- **A11y** : un test dédié `a11y.showcase.test.ts` qui monte la page `/dev/viz-showcase` et passe axe-core (échec si une violation `serious` ou `critical` est détectée).
- **Performance / visual** : la route showcase reste la fixture manuelle ; une mesure LCP automatisée est repoussée à F47 (perf budget).

**Rationale** :
- Couverture 80 % imposée par la constitution.
- axe-core direct sur DOM happy-dom suffit pour la majorité des règles WCAG AA testables statiquement.
- Mesure LCP/FPS est mieux gérée par un harness perf dédié (hors-scope MVP F40).

**Alternatives rejetées** :
- Playwright systématique : surcoût pour cette feature, l'E2E global est traité par F47.
- Snapshots visuels : maintenance lourde, fragile sur charts canvas.

**Ressources** : axe-core API ; Vitest + happy-dom ; @vue/test-utils mount/shallowMount.
