# Phase 1 — Data Model: Design System & Tokens

**Feature**: 036-design-system-tokens
**Date**: 2026-05-02

> **Note** : cette feature ne crée **aucune table base ni colonne**. Le « modèle de données » consiste en un **catalogue de tokens CSS** (variables nommées) qui constitue la source de vérité du design system.

---

## 1. Vue d'ensemble

| Catégorie     | # tokens | Préfixe variable        | Bloc                                 |
|---------------|----------|-------------------------|--------------------------------------|
| Couleurs      | ~52      | `--color-*`             | `:root` + `[data-theme="dark"]`      |
| Typographie   | ~14      | `--font-*`              | `:root`                              |
| Spacing       | 9        | `--space-*`             | `:root`                              |
| Radius        | 6        | `--radius-*`            | `:root`                              |
| Shadows       | 5        | `--shadow-*`            | `:root` + override dark              |
| Motion        | 5        | `--duration-*`, `--ease-*` | `:root`                           |
| Z-index       | 4        | `--z-*`                 | `:root`                              |
| **Total**     | **~95**  |                         |                                      |

Cible NFR : ≤ ~80 tokens visibles à un dev, ~95 incluant les overrides dark.

---

## 2. Couleurs

### 2.1 Neutres (11 nuances, light)

| Token                | Valeur cible (light)   | Usage indicatif                       |
|----------------------|-------------------------|---------------------------------------|
| `--color-neutral-50`  | `#fafafa`               | fond extra-clair                      |
| `--color-neutral-100` | `#f5f5f5`               | fond surface                          |
| `--color-neutral-200` | `#e5e5e5`               | bordure légère                        |
| `--color-neutral-300` | `#d4d4d4`               | bordure défaut                        |
| `--color-neutral-400` | `#a3a3a3`               | placeholder                           |
| `--color-neutral-500` | `#737373`               | texte secondaire                      |
| `--color-neutral-600` | `#525252`               | texte muted                           |
| `--color-neutral-700` | `#404040`               | texte fort                            |
| `--color-neutral-800` | `#262626`               | titre                                 |
| `--color-neutral-900` | `#171717`               | texte principal                       |
| `--color-neutral-950` | `#0a0a0a`               | hover/contrast extrême                |

### 2.2 Brand (9 nuances, vert ESG)

| Token              | Valeur cible (light) | Usage indicatif                       |
|--------------------|-----------------------|---------------------------------------|
| `--color-brand-50`  | `#f0fdf4`             | fond accent ultra-clair               |
| `--color-brand-100` | `#dcfce7`             | badge success surfaces                |
| `--color-brand-200` | `#bbf7d0`             |                                       |
| `--color-brand-300` | `#86efac`             |                                       |
| `--color-brand-400` | `#4ade80`             |                                       |
| `--color-brand-500` | `#16a34a`             | **CTA primaire, focus ring**          |
| `--color-brand-600` | `#15803d`             | hover CTA                             |
| `--color-brand-700` | `#166534`             | active                                |
| `--color-brand-900` | `#14532d`             | texte sur fond brand-100              |

> Valeurs initiales basées sur la palette `green` Tailwind (à valider en revue PM ; ajustables sans refactor).

### 2.3 Sémantiques (4 × 3 = 12 nuances)

| Famille | Tokens                                              | Usage                          |
|---------|------------------------------------------------------|---------------------------------|
| success | `--color-success-50/-500/-700`                       | confirmation, validation       |
| warning | `--color-warning-50/-500/-700`                       | alerte non bloquante           |
| danger  | `--color-danger-50/-500/-700`                        | erreur, suppression            |
| info    | `--color-info-50/-500/-700`                          | message neutre informatif      |

Valeurs cibles initiales (light) — alignées sur Tailwind défaut, à valider :
- success-500 ≈ `#16a34a` (peut alias `brand-500`)
- warning-500 ≈ `#f59e0b`
- danger-500 ≈ `#dc2626`
- info-500 ≈ `#0284c7`

### 2.4 Surface, texte, bordure (rôles sémantiques)

| Token                  | Light (référence)         | Dark (référence)          |
|------------------------|----------------------------|----------------------------|
| `--color-bg`           | `var(--color-neutral-50)` | `var(--color-neutral-950)` |
| `--color-surface`      | `#ffffff`                 | `var(--color-neutral-900)` |
| `--color-text`         | `var(--color-neutral-900)` | `var(--color-neutral-50)`  |
| `--color-text-muted`   | `var(--color-neutral-600)` | `var(--color-neutral-400)` |
| `--color-border`       | `var(--color-neutral-200)` | `var(--color-neutral-800)` |
| `--color-focus-ring`   | `var(--color-brand-500)`   | `var(--color-brand-400)`   |

### 2.5 Override `[data-theme="dark"]`

Le bloc dark redéfinit uniquement les rôles ci-dessus (`--color-bg`, `--color-surface`, `--color-text`, `--color-text-muted`, `--color-border`, `--color-focus-ring`), plus les nuances neutres si nécessaire (inversion 50↔950, 100↔900, etc.). Les sémantiques gardent leurs valeurs (visibles sur fond clair et sombre).

---

## 3. Typographie

| Token                  | Valeur                                  |
|------------------------|------------------------------------------|
| `--font-sans`          | `"Inter", system-ui, …`                  |
| `--font-mono`          | `"JetBrains Mono", ui-monospace, …`      |
| `--font-size-xs`       | `0.75rem` (12 px)                        |
| `--font-size-sm`       | `0.875rem` (14 px)                       |
| `--font-size-base`     | `1rem` (16 px)                           |
| `--font-size-lg`       | `1.125rem` (18 px)                       |
| `--font-size-xl`       | `1.25rem` (20 px)                        |
| `--font-size-2xl`      | `1.5rem` (24 px)                         |
| `--font-size-3xl`      | `1.875rem` (30 px)                       |
| `--font-size-4xl`      | `2.25rem` (36 px)                        |
| `--font-size-5xl`      | `3rem` (48 px)                           |
| `--line-height-body`   | `1.5`                                    |
| `--line-height-heading`| `1.2`                                    |
| `--font-weight-regular`| `400`                                    |
| `--font-weight-medium` | `500`                                    |
| `--font-weight-semibold`| `600`                                   |
| `--font-weight-bold`   | `700`                                    |

> Les valeurs numériques (KPI) appliquent `font-feature-settings: "tnum" 1; font-variant-numeric: tabular-nums;` via la classe utilitaire `.tabular-nums` ou directement en CSS (FR-009).

---

## 4. Spacing (4 px-grid)

| Token         | Valeur            | Notes                  |
|---------------|-------------------|------------------------|
| `--space-1`   | `0.25rem` (4 px)  | base grid              |
| `--space-2`   | `0.5rem`  (8 px)  |                        |
| `--space-3`   | `0.75rem` (12 px) |                        |
| `--space-4`   | `1rem`    (16 px) |                        |
| `--space-6`   | `1.5rem`  (24 px) |                        |
| `--space-8`   | `2rem`    (32 px) |                        |
| `--space-12`  | `3rem`    (48 px) |                        |
| `--space-16`  | `4rem`    (64 px) |                        |
| `--space-24`  | `6rem`    (96 px) | max conteneur section  |

Tout autre palier est interdit (FR-010).

---

## 5. Radius

| Token          | Valeur            | Notes                                |
|----------------|-------------------|--------------------------------------|
| `--radius-sm`  | `0.25rem`  (4 px) | petits éléments                      |
| `--radius-md`  | `0.5rem`   (8 px) | inputs, boutons                      |
| `--radius-lg`  | `0.75rem`  (12 px)| pills                                |
| `--radius-xl`  | `1rem`     (16 px)| cartes courantes                     |
| `--radius-2xl` | `1.25rem`  (20 px)| **cartes par défaut** (FR-011)       |
| `--radius-full`| `9999px`          | avatars, badges                      |

---

## 6. Shadows (5 niveaux)

| Token           | Valeur cible (light)                                            |
|-----------------|------------------------------------------------------------------|
| `--shadow-xs`   | `0 1px 2px 0 rgb(0 0 0 / 0.04)`                                  |
| `--shadow-sm`   | `0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)`|
| `--shadow-md`   | `0 4px 6px -1px rgb(0 0 0 / 0.06), 0 2px 4px -2px rgb(0 0 0 / 0.04)`|
| `--shadow-lg`   | `0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.04)`|
| `--shadow-xl`   | `0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.06)`|

En dark, opacités relevées (`0.3` au lieu de `0.06`) pour rester visibles.

---

## 7. Motion

| Token             | Valeur                                |
|-------------------|----------------------------------------|
| `--duration-fast` | `120ms`                                |
| `--duration-base` | `200ms`                                |
| `--duration-slow` | `320ms`                                |
| `--ease-out`      | `cubic-bezier(0.16, 1, 0.3, 1)`        |
| `--ease-in`       | `cubic-bezier(0.7, 0, 0.84, 0)`        |

`@media (prefers-reduced-motion: reduce)` neutralise `animation-duration` et `transition-duration` à `1ms !important` pour `*, *::before, *::after`.

---

## 8. Z-index

| Token              | Valeur | Usage                    |
|--------------------|--------|--------------------------|
| `--z-base`         | `0`    | flux normal              |
| `--z-dropdown`     | `1000` | dropdown                 |
| `--z-bottom-sheet` | `1100` | bottom sheet (F39)        |
| `--z-modal`        | `1200` | modale, dialog           |
| `--z-toast`        | `1300` | notifications            |

---

## 9. Mapping Tailwind v4 (`@theme`)

Dans `main.css`, après l'import de `tokens.css` :

```css
@theme {
  --color-brand-50:  var(--color-brand-50);
  --color-brand-500: var(--color-brand-500);
  /* … */
  --spacing-1:  var(--space-1);
  --spacing-2:  var(--space-2);
  /* … */
  --radius-sm:  var(--radius-sm);
  /* … */
}
```

Tailwind expose alors `bg-brand-500`, `p-2`, `rounded-2xl`, etc., qui résolvent vers les tokens.

---

## 10. État initial vs état cible

| Aspect           | Avant cette feature           | Après cette feature                         |
|------------------|-------------------------------|---------------------------------------------|
| `tokens.css`     | inexistant                    | ~95 variables (light + dark)                |
| `main.css`       | `@import "tailwindcss"` seul  | `@import tokens.css` + `@import tailwindcss` + `@theme` |
| Polices          | défaut système                | Inter + JetBrains Mono auto-hébergées       |
| Page showcase    | absente                       | `/dev/design-system` (DEV only)             |
| Composable a11y  | absent                        | `useReducedMotion()`                        |
| Garde-fou CI     | absent                        | `check-no-arbitrary.sh` exécuté en `make lint` |
| Logo / favicon   | défaut Nuxt                   | `logo-horizontal.svg` + `symbol.svg`        |

---

## 11. Validation Rules (vérifiées par audit)

- Chaque rôle sémantique de couleur (`success`, `warning`, `danger`, `info`, `brand`) a au moins 3 nuances (50, 500, 700).
- Chaque palier de spacing est multiple de 4 px.
- Aucune valeur arbitraire (hors-tokens) dans `frontend/app/` ou `frontend/components/` (vérifié par `check-no-arbitrary.sh`).
- Tous les couples texte/fond du design system passent WCAG AA (≥4.5:1 corps, ≥3:1 texte large).
- Les polices web sont chargées localement (pas d'URL externe dans `tokens.css`).
