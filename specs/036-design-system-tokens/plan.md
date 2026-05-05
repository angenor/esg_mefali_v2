# Implementation Plan: Design System & Tokens (Fondations UI)

**Branch**: `036-design-system-tokens` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/036-design-system-tokens/spec.md`

## Summary

Poser les fondations design (palette resserrée, typographie soignée, spacing 4 px-grid, rayons, ombres, motion vocabulary, focus, contrastes AA, motion réduit) en un jeu unique de **tokens CSS variables** consommés par **Tailwind v4** via la directive native `@theme`. Aucune lib UI tierce. Livrer une page interne `/dev/design-system` (showcase, désactivée en prod), un composable `useReducedMotion()`, des polices auto-hébergées (Inter + JetBrains Mono), et un linter/grep CI bloquant les valeurs arbitraires hors tokens. Toutes les features UI 037-052 dépendent de cette feuille blanche.

Approche technique : le projet utilise déjà Tailwind v4 (`@tailwindcss/vite`) et `frontend/app/assets/css/main.css` ne contient que `@import "tailwindcss"`. On étend cette base avec un fichier `tokens.css` (~80 variables CSS dans `:root` + un bloc dark sous `[data-theme="dark"]`) et un bloc `@theme` qui expose les tokens à la couche utilitaire Tailwind. Les polices sont posées dans `public/fonts/` et préchargées via `app.head.link`. La page showcase et un composable `useReducedMotion()` rendent l'audit visuel et a11y indépendant.

## Technical Context

**Language/Version**: TypeScript 5.x, Vue 3.5 / Nuxt 4 (Composition API)
**Primary Dependencies**: Nuxt 4, Tailwind v4 (`@tailwindcss/vite`), Pinia, gsap (déjà installé), nuxt-security (déjà configuré). **Aucune** lib UI tierce (Vuetify, PrimeVue, Element interdites par constitution P10 et brainstorm F36).
**Storage**: N/A — feature 100 % frontend, pas de table base, pas d'endpoint backend.
**Testing**: Vitest (unit, déjà configuré dans `frontend/vitest.config.ts`) ; audits manuels Lighthouse + axe DevTools sur la page showcase.
**Target Platform**: Navigateurs récents desktop + smartphone (deux dernières versions majeures Chrome / Edge / Safari / Firefox), avec attention smartphone Android milieu de gamme sur 4G ouest-africaine.
**Project Type**: Web application — extension de la couche UI existante, pas de nouveau projet.
**Performance Goals**: LCP < 1,5 s sur 4G smartphone milieu de gamme ; bundle CSS prod < 30 kB gzipped ; Lighthouse Best Practices ≥ 95 sur `/dev/design-system`.
**Constraints**: Pas de Google Fonts ni CDN externe (FR-024 + CSP `default-src 'self'`) ; tous les tokens accessibles AA ; respect `prefers-reduced-motion` y compris pour gsap ; pas de `console.*` en prod.
**Scale/Scope**: ~80 variables CSS, 1 page showcase, 1 composable, 4 fichiers de polices `.woff2`, 1 logo SVG + 1 favicon, ≤ 3 illustrations spot. Aucune table, aucun endpoint.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Aucune donnée factuelle ESG/financière n'est introduite par cette feature (fondations design uniquement). | ✅ N/A |
| P2 | Multi-tenant RLS | Aucune table métier n'est créée ni lue. | ✅ N/A |
| P3 | Audit log append-only | Aucune mutation métier. | ✅ N/A |
| P4 | Versioning + snapshot candidatures | Aucune entité référentielle. | ✅ N/A |
| P5 | Money typé | Aucun montant. | ✅ N/A |
| P6 | Pivot Indicateur unique | Aucun indicateur ESG. | ✅ N/A |
| P7 | Plateforme fermée aux intermédiaires | Aucun rôle ni endpoint exposé. | ✅ N/A |
| P8 | Édition manuelle + sync LLM | Aucun champ alimenté par LLM. | ✅ N/A |
| P9 | Tool-use LLM fiable | Aucun nouveau tool LLM. | ✅ N/A |
| P10 | UX bottom sheet | Cette feature ne crée pas de saisie ; elle fournit les **tokens et primitives motion** consommés par F39 (Bottom Sheet Engine). Le composable `useReducedMotion()` et la durée `--duration-base` (200 ms) sont prévus pour respecter la règle P10 par les features aval. | ✅ |

**Aucune violation.** Cette feature est une fondation UI sans données, sans rôle, sans tool. Le `Complexity Tracking` reste vide.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + Tailwind v4 ; pas de lib UI tierce.
- CSP `default-src 'self'` impose polices auto-hébergées (FR-024).
- Hébergement prod Europe / Afrique de l'Ouest, pas d'impact sur cette feature.
- Langue UI : française par défaut (page showcase en français).

## Project Structure

### Documentation (this feature)

```text
specs/036-design-system-tokens/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (catalogue de tokens, pas de tables)
├── quickstart.md        # Phase 1 output (procédure dev pour vérifier le DS)
├── contracts/           # Phase 1 — N/A (pas d'API), placeholder README
└── tasks.md             # Phase 2 (non créé par /speckit-plan)
```

### Source Code (repository root)

```text
frontend/
├── app/
│   ├── assets/
│   │   └── css/
│   │       ├── main.css            # MODIFIÉ : import tokens.css avant Tailwind, bloc @theme
│   │       └── tokens.css          # NOUVEAU : ~80 variables CSS (light + dark)
│   ├── composables/
│   │   └── useReducedMotion.ts     # NOUVEAU : détection prefers-reduced-motion + helper gsap
│   ├── pages/
│   │   └── dev/
│   │       └── design-system.vue   # NOUVEAU : showcase tokens (DEV only, gated par NODE_ENV)
│   └── ...
├── public/
│   ├── fonts/                      # NOUVEAU : Inter-{400,500,600,700}.woff2 + JetBrainsMono-{400,500}.woff2
│   ├── illustrations/              # NOUVEAU : ≤ 3 SVG spot pour empty states
│   └── brand/                      # NOUVEAU : logo-horizontal.svg + symbol.svg + favicon.svg
├── nuxt.config.ts                  # MODIFIÉ : preload Inter woff2, htmlAttrs lang=fr déjà ok
└── tests/
    └── unit/
        └── useReducedMotion.spec.ts # NOUVEAU : Vitest

backend/                            # NON MODIFIÉ
.specify/                           # NON MODIFIÉ
.github/workflows/                  # MODIFIÉ : ajout step "no-arbitrary-tailwind" (grep)
```

**Structure Decision** : extension du frontend Nuxt 4 existant. Aucune création de projet, pas de toucher backend. Les fichiers nouveaux sont localisés sous `frontend/app/assets/css/`, `frontend/app/composables/`, `frontend/app/pages/dev/`, `frontend/public/`. Un script CI grep (ou règle ESLint custom légère) sera ajouté pour bloquer `bg-\[#`, `p-\[`, `text-\[#`, etc.

## Complexity Tracking

> Aucune violation constitutionnelle. Section vide.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| —         | —          | —                                   |

## Phase 0 — Outline & Research

Voir [research.md](./research.md) pour l'état des décisions techniques (Tailwind v4 `@theme`, mécanisme dark, fontes auto-hébergées, motion + gsap + reduced-motion, gating CI valeurs arbitraires, page showcase DEV-only).

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — catalogue des tokens (≈80 variables CSS), structure `:root` + `[data-theme="dark"]`, mapping `@theme`. Pas de tables base.
- `contracts/` — **N/A** : feature 100 % frontend, pas d'API. Un fichier `contracts/README.md` documente l'absence et les renvoie vers le data-model des tokens.
- [quickstart.md](./quickstart.md) — procédure dev pour vérifier le design system (lancement `make frontend`, ouverture `/dev/design-system`, axe DevTools, Lighthouse, grep anti-arbitraire).

### Constitution Re-check (post-design)

Inchangé : aucune des 10 principes ne déclenche d'obligation pour cette feature de fondations. ✅

### Agent context update

Le pointeur `<!-- SPECKIT START --> … <!-- SPECKIT END -->` dans `CLAUDE.md` (à la racine projet) sera mis à jour pour pointer sur ce plan : `specs/036-design-system-tokens/plan.md`.

## Phase 2 — Tasks (différé)

Non créé par cette commande ; sera produit par `/speckit-tasks`.
