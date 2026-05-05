# Codemap — Frontend UI Primitives (F37)

> Spec : [specs/037-ui-primitives/](../../specs/037-ui-primitives/) · Statut : _done_ (2026-05-03)
> Stack : Nuxt 4 (Composition API) + Pinia + Tailwind v4 + tokens F36 + `@floating-ui/vue` + `vee-validate` + `zod` + `dompurify` + `gsap` (dynamique).

## Localisation

```
frontend/app/
├── components/ui/         # 27 atomes Ui*.vue (auto-import préfixe Ui)
├── composables/           # composables transverses F37
├── utils/sanitize.ts      # wrapper DOMPurify
├── types/ui.ts            # types publics UiSize, UiOption, …
├── middleware/dev-only.ts # guard pour les pages /dev/*
└── pages/dev/             # showcase + démos non publiées en prod
frontend/tests/
├── unit/ui/               # un *.spec.ts par atome
├── unit/composables/      # tests des composables F37
└── integration/           # showcase-a11y (axe-core), sheet-ca, manuels MD
```

## Atomes (27)

| Catégorie | Atomes |
|---|---|
| Action | `UiButton` |
| Saisie texte | `UiInput`, `UiTextarea`, `UiNumber` |
| Sélection | `UiSelect`, `UiCombobox`, `UiMultiSelect`, `UiRadioGroup`, `UiCheckboxGroup`, `UiSwitch`, `UiSlider` |
| Date | `UiDatePicker`, `UiDateRangePicker` |
| Surface / overlay | `UiModal`, `UiPopover`, `UiTooltip`, `UiToast`, `UiToastHost` |
| Présentation | `UiCard`, `UiBadge`, `UiTag`, `UiAvatar`, `UiEmptyState` |
| Feedback | `UiSkeleton`, `UiSpinner`, `UiProgress` |
| Composition | `UiFormField` (slot props avec `id`, `state`, ARIA) |
| Upload | `UiFileUpload` |

## Composables transverses

| Composable | Rôle | Réf. |
|---|---|---|
| `useFieldId` | génère un id stable SSR-safe | R-014 |
| `useFloating` | wrapper typé sur `@floating-ui/vue` (flip + offset + autoUpdate) | R-002 |
| `useFocusTrap` | focus trap accessible avec restauration de focus | R-003 |
| `useToast` | singleton FIFO bornée (5) avec auto-dismiss | R-008 |
| `useMoneyFormat` | format/parse XOF/EUR/USD via `Intl.NumberFormat` | R-012 |
| `useReducedMotion` | observe `prefers-reduced-motion` | — |

## Pages dev (DEV-only)

| Route | But |
|---|---|
| `/dev/components` | showcase des 27 atomes (auditée par axe-core) |
| `/dev/form-candidature` | parcours US1 — formulaire candidature dense |
| `/dev/sheet-ca` | parcours US2 — bottom-sheet "Renseigner CA" + vee-validate/zod |

Le middleware `app/middleware/dev-only.ts` renvoie 404 si `NODE_ENV === 'production'`.

## Tests

- Unitaires : `pnpm vitest run` (216 tests, 39 fichiers).
- Coverage : `pnpm vitest run --coverage` ≥ 80 % (lines 92, branches 81, functions 81).
- A11y : `tests/integration/showcase-a11y.spec.ts` (axe-core, 0 violation critique/sérieuse — WCAG 2.1 AA).
- Manuels : `tests/integration/showcase-keyboard.manual.md`, `screenreader-a11y.manual.md`, `form-candidature.manual.md`.

## Conventions

- Naming : `Ui<Nom>.vue`, `use<Nom>`, types `Ui<Nom>`.
- API publique gelée (FR-024) — voir `specs/037-ui-primitives/contracts/component-api.md`.
- Tous les visuels passent par les tokens F36 (`var(--color-…)`, `var(--space-…)`, etc.) — pas de valeur en dur.
- `prefers-reduced-motion` respecté sur toute animation.
- Aucun `v-html` brut hors `utils/sanitize.ts`.

## Dépendances runtime ajoutées

`@floating-ui/vue`, `dompurify`, `vee-validate`, `@vee-validate/zod`, `zod`.
Dev : `@types/dompurify`, `@testing-library/vue`, `axe-core`.
