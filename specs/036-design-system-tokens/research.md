# Phase 0 — Research: Design System & Tokens

**Feature**: 036-design-system-tokens
**Date**: 2026-05-02
**Status**: Resolved (aucun NEEDS CLARIFICATION restant)

Ce document consolide les décisions techniques pour les fondations design.
Chaque entrée suit le format **Décision / Rationale / Alternatives**.

---

## R1 — Mécanisme tokens : CSS variables + Tailwind v4 `@theme`

**Décision** : déclarer ~80 variables CSS dans un fichier `tokens.css` chargé avant `@import "tailwindcss"`, puis exposer ces variables à Tailwind v4 via la directive native `@theme { … }` (placée dans `main.css`). La couche utilitaire Tailwind résout les classes (`bg-brand-500`, `text-success-700`) en lisant directement les variables.

**Rationale** :
- Tailwind v4 supporte nativement `@theme` (introduite en v4) et n'exige plus de fichier `tailwind.config.ts`.
- CSS variables sont chargées sans coût JS, supportent `prefers-color-scheme` et un override `[data-theme="dark"]`.
- Une seule source de vérité (`tokens.css`) — un changement de palette ne demande pas de refactor (FR-001, SC-001).

**Alternatives** :
- `tailwind.config.ts` JS — rejeté : Tailwind v4 le considère legacy, et duplique les valeurs.
- Sass variables — rejeté : compile-time, pas de bascule runtime ni dark mode.
- Style Dictionary — rejeté : surdimensionné pour 80 tokens, ajoute une étape build.

---

## R2 — Stratégie dark mode : tokens prêts, bascule désactivée

**Décision** : le bloc `:root { … }` contient les tokens light. Un bloc `[data-theme="dark"]` redéfinit les couleurs neutres et brand pour le dark. Au MVP, **aucun bouton de bascule** n'est exposé (FR-015). Les tokens dark sont validés via inspection manuelle DevTools (poser temporairement l'attribut sur `<html>`).

**Rationale** :
- Permet de livrer un MVP light only sans recoder pour le dark futur.
- Évite le `prefers-color-scheme` automatique qui pourrait surprendre les utilisateurs PME.
- L'attribut `data-theme` est plus robuste qu'une classe `.dark` (lisible côté serveur SSR Nuxt).

**Alternatives** :
- `prefers-color-scheme` automatique — rejeté : non testé pour le MVP, risque visuel.
- Classe `.dark` (Tailwind classique) — équivalent, mais `data-theme` reste lisible HTML pur.

---

## R3 — Polices auto-hébergées (Inter + JetBrains Mono)

**Décision** :
- Police principale : **Inter** (woff2, weights 400/500/600/700, latin + latin-ext).
- Police monospace : **JetBrains Mono** (woff2, weights 400/500).
- Fichiers servis depuis `frontend/public/fonts/`, déclarés dans `tokens.css` via `@font-face` avec `font-display: swap`.
- Inter Regular 400 préchargé via `nuxt.config.ts` → `app.head.link`.

**Rationale** :
- CSP `default-src 'self'` (déjà active dans `nuxt.config.ts`) interdit Google Fonts (FR-024).
- `font-display: swap` évite FOIT (Flash Of Invisible Text) et garde un LCP < 1,5 s sur 4G (SC-004).
- Inter couvre tous les diacritiques français + œ + caractères latins étendus.

**Alternatives** :
- Geist Sans — esthétiquement proche, mais licence et empreinte glyphes moins testées en finance.
- IBM Plex Sans — bonne lisibilité, plus institutionnel, gardé en plan B documenté dans Assumptions.
- Google Fonts CDN — rejeté (CSP + RGPD : transfert IP vers Google).

---

## R4 — Motion : tokens de durée + composable `useReducedMotion()`

**Décision** :
- Tokens de durée : `--duration-fast: 120ms`, `--duration-base: 200ms`, `--duration-slow: 320ms`.
- Tokens d'easing : `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)`, `--ease-in: cubic-bezier(0.7, 0, 0.84, 0)`.
- Composable `useReducedMotion()` retourne `Ref<boolean>` basé sur `window.matchMedia('(prefers-reduced-motion: reduce)')`.
- Helper `gsapDuration(d)` : si reduced, renvoie `0` ; sinon `d`. Idem pour `gsap.set` vs `gsap.to`.
- CSS global : `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 1ms !important; transition-duration: 1ms !important; } }` neutralise les animations CSS non-essentielles.

**Rationale** :
- Couvre FR-014 et FR-020 : impose le respect de `prefers-reduced-motion` sur **CSS et gsap**.
- Les durées 120/200/320 ms restent perceptibles sans saturer (étalonnage Linear/Vercel).

**Alternatives** :
- VueUse `useReducedMotion` — possible, mais le projet ne l'a pas comme dépendance ; ré-implémentation triviale (12 lignes) évite une dépendance.

---

## R5 — Garde-fou contre valeurs arbitraires (FR-003, SC-002)

**Décision** : ajouter un script shell `frontend/scripts/check-no-arbitrary.sh` exécuté en CI :

```bash
#!/usr/bin/env bash
# Échoue si des valeurs arbitraires Tailwind apparaissent dans les sources.
PATTERNS='bg-\[#|text-\[#|border-\[#|p-\[|m-\[|w-\[|h-\[|rounded-\['
if grep -RnE "$PATTERNS" frontend/app frontend/components 2>/dev/null; then
  echo "ERREUR : valeur arbitraire Tailwind détectée. Utiliser les tokens." >&2
  exit 1
fi
```

Intégré dans `Makefile` cible `lint` et dans le workflow GitHub Actions `frontend.yml` (à compléter à l'implémentation).

**Rationale** :
- Léger, sans dépendance ESLint custom (qui demanderait un parser AST).
- Couvre 80 % des dérives observées en pratique.

**Alternatives** :
- Plugin ESLint custom — rejeté MVP : surdimensionné, latence dev.
- Stylelint — rejeté : couvre CSS, pas les classes Tailwind dans `.vue`.

---

## R6 — Page showcase `/dev/design-system` (DEV-only)

**Décision** : page Vue dans `frontend/app/pages/dev/design-system.vue`. Son rendu est conditionné par `process.env.NODE_ENV !== 'production'` ; en production, la route renvoie une 404 via un `definePageMeta({ middleware: 'dev-only' })` ou un simple test côté setup. Sections obligatoires : Palette neutre, Palette brand, Sémantiques, Typographie (échelle + tabular-nums), Spacing, Radius, Shadows, Motion (boutons démo + indicateur reduced-motion), Focus (clavier), États désactivés, Iconographie (Heroicons outline), Logo, Empty states.

**Rationale** :
- Référence vivante (FR-021, SC-006).
- DEV-only évite d'exposer la marque en production (FR-022).

**Alternatives** :
- Storybook — rejeté MVP (hors-scope explicite F36).
- Page publique en prod — rejeté : non utile aux PME.

---

## R7 — Iconographie : Heroicons outline 24

**Décision** : utiliser **Heroicons** v2 (outline 24 px) via le package `@heroicons/vue` (à ajouter dans `package.json` lors de l'implémentation). Solid 24 réservé aux états sélectionnés.

**Rationale** :
- Cohérent avec le ton Linear/Vercel/Stripe ciblé.
- Licence MIT, copie locale possible.
- Style outline uniforme sans mélange.

**Alternatives** :
- Lucide — équivalent, légèrement plus dessiné. Heroicons gardé pour cohérence avec l'esthétique sobre brief.
- Phosphor — trop varié.

---

## R8 — Logo et favicon

**Décision** : déposer dans `frontend/public/brand/` :
- `logo-horizontal.svg` (light + dark variants : `logo-horizontal-light.svg`, `logo-horizontal-dark.svg`)
- `symbol.svg` (favicon source SVG)
- Génération `favicon.ico` 16/32/48 et `apple-touch-icon.png` 180.

Wordmark **« ESG Mefali »** en Inter SemiBold 600. Symbol : feuille verte stylisée à valider en revue produit.

**Rationale** : FR-017. Source SVG = un seul fichier de vérité, déclinaisons rasterisées générées.

**Alternatives** : logo PNG only — rejeté (dégradation Retina + mode sombre incompatible).

---

## R9 — Illustrations spot

**Décision** : 3 illustrations SVG max stockées dans `frontend/public/illustrations/` :
1. `empty-list.svg` — listes vides (candidatures, projets).
2. `no-results.svg` — recherche sans résultat.
3. `welcome.svg` — onboarding première connexion.

Style : trait fin, palette neutre + une touche brand, format carré 320×320.

**Rationale** : FR-016. Garde la sobriété ; évite d'ajouter une lib tierce d'illustrations.

**Alternatives** : Lottie — hors-scope F36 ; unDraw — packs trop colorés.

---

## R10 — Préchargement Inter woff2

**Décision** : ajouter dans `nuxt.config.ts → app.head.link` :

```ts
{ rel: 'preload', as: 'font', type: 'font/woff2', href: '/fonts/Inter-Regular.woff2', crossorigin: 'anonymous' }
```

**Rationale** : SC-004 (LCP < 1,5 s). Préchargement uniquement du Regular 400 ; les autres weights sont chargés à la demande via `font-display: swap`.

**Alternatives** : précharger 4 weights — rejeté : coûteux pour une 4G dégradée.

---

## R11 — Test du composable `useReducedMotion`

**Décision** : test Vitest unique dans `frontend/tests/unit/useReducedMotion.spec.ts` qui mock `window.matchMedia` et vérifie que la valeur initiale est correcte + que le `change` event update le `Ref`.

**Rationale** : couverture du seul morceau JS testable de la feature ; SC-008 vérifié manuellement sur la page showcase.

**Alternatives** : E2E Playwright — hors-scope MVP de cette feature, sera couvert par F052+ tests E2E.

---

## Tableau récap des décisions

| ID  | Sujet                          | Décision retenue                                                |
|-----|-------------------------------|------------------------------------------------------------------|
| R1  | Tokens                        | CSS vars + Tailwind v4 `@theme`                                 |
| R2  | Dark mode                     | `[data-theme="dark"]`, bascule désactivée MVP                   |
| R3  | Polices                       | Inter + JetBrains Mono auto-hébergées                           |
| R4  | Motion                        | Tokens durée/easing + `useReducedMotion()` + override CSS       |
| R5  | Garde-fou Tailwind             | Script shell grep en CI                                         |
| R6  | Showcase                      | `/dev/design-system`, DEV-only                                   |
| R7  | Iconographie                  | Heroicons v2 outline 24                                         |
| R8  | Logo                          | SVG + favicon SVG, déclinaisons light/dark                      |
| R9  | Illustrations                 | 3 SVG spot pour empty states                                    |
| R10 | LCP                           | Preload Inter Regular woff2                                     |
| R11 | Test                          | Vitest sur `useReducedMotion()`                                 |

Aucun NEEDS CLARIFICATION restant. Phase 1 peut démarrer.
