# F36 — Design System & Tokens

**Phase** : A — Fondations design (UI MVP)
**Modules brainstorm** : transversal — préalable à toutes les features UI 36-56
**Dépendances** : F01 (Tailwind v4 installé)
**Estimation** : 2 jours
**Statut** : planned → in-implementation (voir [specs/036-design-system-tokens/](../../specs/036-design-system-tokens/)) — F37+ peuvent dépendre de cette fondation

## Contexte et objectif

Avant de coder une page, on pose **un design system unique et épuré**. Toute la suite (chat, dashboards, formulaires, rapports, page publique `/verify`) doit s'y conformer. Le but : une UI **soignée, sobre, lisible, qui inspire confiance** à des dirigeants de PME ouest-africaines en finance verte. Le ton est entre **Linear / Vercel / Stripe Press** : minimal, beaucoup d'espace blanc, typo soignée, accent vert très contenu, animations courtes (≤200 ms).

Aucune lib UI tierce (Vuetify, PrimeVue, Element). Tout est **Tailwind v4 + composants maison** stylés via tokens CSS.

## User Stories

### US1 — Tokens centralisés (P1)
**En tant que** dev frontend, **je veux** que toutes les couleurs, espacements, rayons, ombres, polices, durées d'animation soient déclarés une seule fois (CSS variables + Tailwind config), **afin que** changer la palette ne demande pas de refactor.

### US2 — Palette signature (P1)
Palette resserrée :
- Neutres : 11 nuances (`neutral-50` → `neutral-950`) — base de l'UI.
- Brand : un seul vert ESG (`brand-50` → `brand-900`) — usage parcimonieux (CTA, success, accents).
- Sémantiques : `success`, `warning`, `danger`, `info` — chacun 3 nuances (50/500/700).

### US3 — Typographie (P1)
- Police principale : **Inter** (self-hosted woff2, weights 400/500/600/700).
- Police mono : **JetBrains Mono** ou **Geist Mono** (KPI, valeurs numériques).
- Échelle modulaire 1.125× : `xs 12 / sm 14 / base 16 / lg 18 / xl 20 / 2xl 24 / 3xl 30 / 4xl 36 / 5xl 48`.
- Line-height 1.5 corps, 1.2 titres. `tabular-nums` actif sur valeurs numériques.

### US4 — Spacing 4 px-grid (P1)
Paliers Tailwind autorisés uniquement : `1 / 2 / 3 / 4 / 6 / 8 / 12 / 16 / 24` (4 → 96 px). Interdire les valeurs arbitraires.

### US5 — Rayons & ombres (P1)
- Radius : `sm 4 / md 8 / lg 12 / xl 16 / 2xl 20 / full`. Cartes par défaut `rounded-2xl`.
- Shadows : 5 niveaux subtils RGBA très basse opacité. Pas d'ombres « néon ».

### US6 — Motion vocabulary (P1)
Timings : `fast 120 ms`, `base 200 ms`, `slow 320 ms`. Easings `ease-out` (entrée), `ease-in` (sortie). `prefers-reduced-motion` neutralise toutes les transitions non-essentielles.

### US7 — Dark mode strategy (P2)
Class-based `dark:`. Tokens auto-mappés. MVP livré en **light only** mais tokens dark prêts.

### US8 — Brand voice & illustrations (P1)
Photos sobres, **Heroicons** (outline 24 / solid 24) seulement, illustrations spot custom uniquement pour les empty states (max 3). Logo horizontal + symbol-only pour favicon.

### US9 — Accessibilité baseline (P1)
Contraste AA partout (4.5:1 corps, 3:1 large). Focus ring 2 px brand-500 + offset 2 px. Tab order, ESC global.

## Exigences fonctionnelles

- **FR-001** : `frontend/app/assets/css/tokens.css` → ~80 variables CSS (`--color-*`, `--space-*`, `--radius-*`, `--shadow-*`, `--font-*`, `--duration-*`, `--ease-*`).
- **FR-002** : `tailwind.config.ts` lit `tokens.css` via `@theme` (Tailwind v4 native). Aucun token dupliqué.
- **FR-003** : Page interne `/dev/design-system` (DEV only) — référence vivante, rend tous les tokens.
- **FR-004** : Lint / grep CI interdit valeurs arbitraires (`bg-[#abc]`, `p-[7px]`).
- **FR-005** : Couleurs sémantiques only (jamais `bg-green-500`, toujours `bg-success-500`).
- **FR-006** : Polices self-hostées dans `public/fonts/`, `font-display: swap`. Aucune requête Google Fonts.
- **FR-007** : Composable `useReducedMotion()` neutralise gsap si user préfère.

## Exigences non-fonctionnelles

- **NFR-001** : Lighthouse "Best Practices" ≥ 95 sur le showcase.
- **NFR-002** : Bundle CSS final < 30 kB gzipped (Tailwind purge OK).
- **NFR-003** : LCP < 1.5 s sur mobile 4G (préchargement Inter woff2).
- **NFR-004** : Aucun `console.*` en prod.

## Composants livrés

- `assets/css/tokens.css`
- `assets/css/main.css` (imports + Tailwind)
- `tailwind.config.ts`
- `pages/dev/design-system.vue` (showcase)
- `composables/useReducedMotion.ts`
- `public/fonts/{inter,jetbrains-mono}.woff2`

## Success Criteria

- **SC-001** : `/dev/design-system` rend toutes les sections sans erreur console.
- **SC-002** : `git grep "bg-\[#"` retourne 0.
- **SC-003** : Build prod respecte NFR-002.
- **SC-004** : Lighthouse audit passe.

## Hors-scope MVP

- Storybook → post-MVP.
- Dark mode actif → tokens prêts, basculement hidden.
- Internationalisation typographique non-latine → post-MVP.
- Lottie / animations vidéo.

## Risques et points de vigilance

- **Dérive** : un dev ajoute une couleur custom → ESLint rule + revue PR sur tout `*.vue` ajoutant une couleur.
- **Tailwind v4 instabilité** : verrouiller version exacte dans `package.json`.
- **Inter trop générique** : valider avec PM avant de figer ; alternatives Geist Sans, IBM Plex Sans.
