# Phase 0 — Research: UI Primitives Library (F37)

Spec : [spec.md](./spec.md) · Plan : [plan.md](./plan.md)
Date : 2026-05-02

## R-001 — Stratégie de bibliothèque : maison vs wrap d'une lib tierce

**Decision** : Atomes 100 % maison sous `frontend/app/components/ui/`, inspirés de `shadcn/ui` (on possède le code).
**Rationale** : la spec et la constitution figent la stack (Nuxt 4 + Tailwind v4 + gsap) et exigent une UX très spécifique (bottom-sheet F39, prefers-reduced-motion strict, FR par défaut, tokens F36). Wrapper PrimeVue/Vuetify ajouterait des kB inutiles, contournerait les tokens, et figerait des décisions d'a11y qui doivent rester sous notre contrôle.
**Alternatives** : `radix-vue`/`reka-ui` (headless) — rejeté pour ne pas imposer une couche d'abstraction supplémentaire ; `PrimeVue` (poids, theming concurrent de Tailwind v4) ; `Vuetify` (Material Design imposé).

## R-002 — Positionnement (Tooltip, Popover, Combobox menu)

**Decision** : `@floating-ui/vue` (1.x).
**Rationale** : standard de fait, SSR-safe, supporte `flip`, `shift`, `offset`, `arrow`, `autoUpdate`, `virtualElement`. Maintenu, léger (~7 kB gzipped pour la part Vue).
**Alternatives** : code maison (rejeté — risque visuel) ; `popper.js v2` (déprécié) ; `@vueuse/core` (n'embarque pas le placement).
**Wrapper interne** : `composables/useFloating.ts` qui expose `{ floatingRef, referenceRef, x, y, strategy, placement, update }` typés et applique nos placements par défaut (`bottom-start` pour Combobox, `top` pour Tooltip).

## R-003 — Focus trap (Modal)

**Decision** : composable maison `useFocusTrap.ts` (~80 LOC) : sélection des focusables (`[tabindex]:not([tabindex="-1"]), input, select, textarea, button, a[href]`) + listener `keydown` Tab/Shift+Tab.
**Rationale** : la lib `focus-trap` ferait l'affaire mais ajoute une dépendance pour ~80 lignes ; besoin borné (Modal + listbox de Combobox).
**Alternatives** : `focus-trap` (acceptable fallback si bug majeur) ; `@vueuse/core useFocusTrap` (acceptable mais tire toute la lib).

## R-004 — Date pickers

**Decision** : input HTML natif `<input type="date">` pour `UiDatePicker`. Calendrier custom léger pour `UiDateRangePicker` (deux mois côte-à-côte, locale FR via `Intl.DateTimeFormat('fr-FR')`).
**Rationale** : `<input type="date">` couvre 95 % des besoins, est nativement accessible et localisé, zéro dépendance. Pas d'équivalent natif consensuel pour le range — on l'écrit à la main contre `Intl`.
**Alternatives** : `vuepic/vue-datepicker` (~30 kB, conflit thème) ; `flatpickr` (non-Vue, wrappers fragiles).

## R-005 — Sanitization

**Decision** : `dompurify` 3.x via wrapper `utils/sanitize.ts` exposant `sanitizeHtml(html, { allowList })`. Convention : tout `v-html` doit appeler ce helper ou être interdit en revue (ESLint rule custom à viser plus tard, hors scope F37).
**Rationale** : DOMPurify est la référence ; ~12 kB gzipped, tree-shakable. Wrapper unique = point de contrôle revue + tests.
**Alternatives** : `sanitize-html` (Node-oriented), `xss` (moins maintenu).

## R-006 — Validation déclarative (UiFormField)

**Decision** : `vee-validate` 4.x + `zod` (via `@vee-validate/zod`). `UiFormField` consomme `useField` (slot prop `state`) et expose les hooks de présentation (`error`, `meta.dirty`, `meta.valid`).
**Rationale** : standard Vue, support TS first-class, intégration zod sans friction. Aucune logique de validation embarquée dans F37 — F37 fournit la couche de présentation.
**Alternatives** : `formkit` (lib UI complète — concurrence directe avec F37, rejeté) ; validation maison (rejeté — réinventer la roue).

## R-007 — Animations + reduced-motion

**Decision** : gsap 3.12 (déjà installé) avec court-circuit systématique via `useReducedMotion()` (déjà présent — `gsapDuration(d, reduced)` retourne 0 si reduced). Convention : tout composant animé importe `useReducedMotion` et passe sa durée à travers ce helper.
**Rationale** : composable existant et testé.
**Alternatives** : transitions CSS pures (envisagé pour Skeleton shimmer — voir R-009).

## R-008 — Toast queue

**Decision** : composable singleton `useToast()` exposant `{ push(toast), dismiss(id), toasts }` ; état partagé via un `reactive()` au niveau module (Nuxt-friendly côté client). Un `<UiToastHost />` placé dans `app.vue` (ou layout par défaut) monte la file et gère portail + animations.
**Rationale** : pas besoin de Pinia pour cet état purement éphémère ; un singleton module suffit. SSR-safe : le module ne touche au DOM qu'au montage de l'host.
**Alternatives** : Pinia store (overkill) ; provide/inject (oblige les consommateurs à recevoir le toaster en prop, friction).
**Bornes** : 5 toasts visibles max, file FIFO, auto-dismiss 5 s configurable, `aria-live="polite"` pour info/success, `aria-live="assertive"` pour error.

## R-009 — Skeleton shimmer sans gsap

**Decision** : animation CSS pure (`@keyframes` + `background-position`) ; `prefers-reduced-motion: reduce` la coupe via media query CSS.
**Rationale** : zéro JS, parfaitement répété, pas besoin de gsap pour un dégradé qui glisse.
**Alternatives** : gsap (overkill).

## R-010 — Virtualisation Combobox

**Decision** : virtualisation maison minimale dans `UiCombobox` quand `options.length > 100` (rendu fenêtré : ~20 items autour du focus). Si la complexité dérape, fallback à `vue-virtual-scroller`.
**Rationale** : éviter une dépendance pour un cas borné. La logique fenêtrée (itemHeight constant + offset) est ~50 LOC.
**Alternatives** : `vue-virtual-scroller` (~10 kB) — acceptable s'il faut aussi virtualiser MultiSelect avec items de hauteur variable.

## R-011 — Audit accessibilité automatisé

**Decision** : `axe-core` 4.x exécuté sur `/dev/components` via un test vitest dédié (`tests/integration/showcase-a11y.spec.ts`).
**Rationale** : ancre SC-002 (zéro violation critique/sérieuse) dans la CI sans dépendre d'un humain.
**Alternatives** : `pa11y` (plus lourd) ; Lighthouse a11y (couplé navigateur, hors scope).

## R-012 — `UiNumber` masque FCFA/EUR

**Decision** : composable `useMoneyFormat({ currency, locale })` qui retourne `{ display(raw), parse(input) }` basé sur `Intl.NumberFormat`. Pour FCFA, `Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF' })`. Le composant garde la valeur numérique en `modelValue` ; l'affichage reste formaté en lecture, repasse en clair en édition.
**Rationale** : zéro dépendance, locale-aware, conforme P5 (le typage `Decimal` reste côté parent).
**Alternatives** : `cleave.js` (poids inutile), `vue-currency-input` (lib UI concurrente).

## R-013 — Outillage de test

**Decision** :
- `vitest` (déjà installé) + `happy-dom` (déjà installé) pour 95 % des tests unitaires d'atomes.
- `@testing-library/vue` à ajouter pour les assertions a11y (`getByRole`, `getByLabelText`).
- `axe-core` à ajouter pour l'audit auto.
- Pour les tests qui exigent un vrai DOM (focus trap réel, gsap motion), basculer ces specs sous Playwright si happy-dom devient limitant — décision repoussée à l'implémentation.

**Rationale** : minimiser les nouvelles dépendances. Préférer happy-dom → Playwright uniquement si bloquant.

## R-014 — Page showcase `/dev/components`

**Decision** : route Nuxt `pages/dev/components.vue`, gardée par un middleware `dev-only` qui retourne 404 si `process.env.NODE_ENV === 'production'`. Render simple : un `<UiCard>` par atome, contenant variants + contrôles minimaux (toggles `disabled`, `loading`, `size`).
**Rationale** : pas besoin de Storybook (poids, double config). Une page Nuxt couvre showcase + audit + démo manuelle.
**Alternatives** : Histoire (Storybook-like Vue) — envisageable post-MVP ; rejeté ici pour rester sobre.

## R-015 — Convention de tests par atome

**Decision** : chaque atome a `tests/unit/ui/Ui<Name>.spec.ts` couvrant :
1. rendu par défaut (snapshot ARIA pertinent),
2. chaque variante de prop publique,
3. chaque event émis,
4. clavier (au minimum Tab et Enter/Esc selon pertinence),
5. attributs ARIA pertinents (`aria-disabled`, `aria-invalid`, `aria-describedby`, `role`, etc.).
**Rationale** : ancre SC-005 (≥ 80 % couverture) et FR-005 (events nommés explicites).

## R-016 — Stabilité d'API (FR-024)

**Decision** : `contracts/component-api.md` (dans le spec dir) fige la convention transverse (props standard, events standard, slots standard) ; toute évolution casse-API passe par un amendement explicite référencé dans `data-model.md`. Pas de versionnage sémantique formel à ce stade — la lib est interne au monorepo.
**Rationale** : F37 est consommée par toutes les autres features. Un breaking change non balisé déclenche une cascade de refactos.
**Alternatives** : versionnage npm interne (rejeté — overengineering monorepo).

## Récapitulatif des dépendances à ajouter

| Paquet | Version cible | Usage | Justification |
|---|---|---|---|
| `@floating-ui/vue` | ^1.1 | Tooltip, Popover, Combobox | R-002 |
| `dompurify` | ^3.1 | wrapper sanitize | R-005 |
| `@types/dompurify` | ^3.0 | types DOMPurify | R-005 |
| `vee-validate` | ^4.13 | UiFormField (pile validation) | R-006 |
| `@vee-validate/zod` | ^4.13 | adaptateur zod | R-006 |
| `zod` | ^3.23 | schémas validation | R-006 |
| `@testing-library/vue` | ^8.x | tests a11y | R-013, R-015 |
| `axe-core` | ^4.10 | audit a11y showcase | R-011 |

Aucune dépendance UI tierce n'est ajoutée. Toutes les libs ci-dessus sont soit headless soit utilitaires.

## Risques et mitigations

| Risque | Mitigation |
|---|---|
| API instable cascade les refactos | FR-024 + `contracts/component-api.md` figés avant adoption massive (R-016). |
| SSR + gsap (accès `window`) | gsap importé dynamiquement dans `onMounted` ; `useReducedMotion` déjà SSR-safe. |
| Bundle gonflé par auto-imports | Nuxt 4 tree-shake les composants non utilisés ; vérifier sur `/login` (SC-006). |
| A11y régressions sans audit en CI | `axe-core` test (R-011) + revue manuelle VoiceOver/NVDA sur Modal et Combobox (SC-009). |
| Floating UI breaking change | pin majeur dans `package.json`. |
| DOMPurify schemas modifiés ad hoc | wrapper unique `utils/sanitize.ts` + revue obligatoire pour tout `v-html`. |
