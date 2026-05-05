# Implementation Plan: UI Primitives Library (F37)

**Branch**: `037-ui-primitives` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/037-ui-primitives/spec.md`

## Summary

Construire 27 atomes UI maison sous `frontend/app/components/ui/Ui<Name>.vue`, auto-importés par Nuxt 4, stylés exclusivement avec les tokens F36 (CSS custom properties + Tailwind v4), accessibles AA, animés via gsap avec respect strict de `prefers-reduced-motion` (composable `useReducedMotion` déjà présent), avec contrats de props/events/slots figés et 80 % de couverture vitest. Une page `/dev/components` (DEV only) sert de showcase et de support d'audit a11y. Aucune dépendance UI tierce ; positionnement délégué à `@floating-ui/vue`, sanitization à `dompurify`, validation déléguée à VeeValidate + zod (consommée côté `UiFormField`).

## Technical Context

**Language/Version** : TypeScript 5.x + Vue 3.5 (Composition API, `<script setup>`)
**Primary Dependencies** : Nuxt 4 (auto-imports), Tailwind v4 (`@tailwindcss/vite`), gsap 3.12, `@floating-ui/vue` (à ajouter), `dompurify` + `@types/dompurify` (à ajouter), VeeValidate + zod (à ajouter, consommé par `UiFormField`).
**Storage** : N/A — aucun atome ne touche à la base. Toast queue = état runtime in-memory (composable partagé `useToast`, voir research.md).
**Testing** : `vitest` 2.x + `@vue/test-utils` 2.x + `happy-dom` (déjà installés) ; `@testing-library/vue` à ajouter pour des assertions a11y orientées comportement ; `axe-core` à ajouter pour audit automatisé sur la showcase.
**Target Platform** : navigateurs evergreen (Chromium 120+, Safari 17+, Firefox 120+) ; viewports mobile 320 → 768 et desktop 768 → 1920 ; SSR activé (Nuxt 4) — atomes safe SSR (pas d'accès `window`/`document` au top-level).
**Project Type** : web application (frontend Nuxt 4 + backend FastAPI). F37 ne touche QUE le frontend.
**Performance Goals** : 60 fps sur ouvertures de modal/popover ; rendu showcase 27 atomes < 1 s sur Macbook M1 ; bundle JS imputable aux primitives utilisées par `/login` < 60 kB gzipped (SC-006).
**Constraints** : zéro lib UI tierce (pas de PrimeVue / Vuetify / shadcn-vue / radix-vue) ; SSR-safe ; `prefers-reduced-motion` strict ; pas de `v-html` non sanitizé ; pas d'appel réseau dans un atome.
**Scale/Scope** : 27 atomes × ~2 fichiers (composant + test) + composables + utils ≈ 70 fichiers ; ~50 features et pages downstream qui consommeront la lib.

## Constitution Check

Référence : [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle introduite par cette feature pointe-t-elle vers une `Source` `verified` ? | ✅ N/A — aucune donnée métier introduite ; les atomes affichent ce qu'on leur passe. |
| P2 | Multi-tenant RLS | Toute nouvelle table métier porte-t-elle `account_id` + RLS ? | ✅ N/A — aucune table créée. |
| P3 | Audit log append-only | Toute mutation introduite est-elle journalisée ? | ✅ N/A — aucune mutation backend. |
| P4 | Versioning + snapshot candidatures | Versioning des nouveaux référentiels ? | ✅ N/A — aucun référentiel touché. |
| P5 | Money typé | `Money = {amount: Decimal, currency}` côté présentation ? | ✅ `UiNumber` accepte un `mode='money'` + slot devise ; il **n'effectue aucun calcul** et délègue le typage `Decimal` au consommateur (FormField + zod côté parent). |
| P6 | Pivot Indicateur unique | ESG par axe ? | ✅ N/A. |
| P7 | Plateforme fermée aux intermédiaires | Pas de rôles externes ? | ✅ N/A — primitives neutres. |
| P8 | Édition manuelle + sync LLM | Champs LLM modifiables ? | ✅ Toutes les saisies F37 sont nativement éditables ; aucun atome n'est en lecture seule par défaut autre que par `:readonly`. |
| P9 | Tool-use LLM fiable | Nouveaux tools LLM ? | ✅ N/A — aucun tool LLM ajouté. |
| P10 | UX bottom sheet | Composants interactifs en bottom-sheet ? | ✅ F37 fournit les **atomes** que F39 placera dans la sheet. La spec rappelle que les atomes ne sont pas auto-portés en inline-bulle (interdiction relayée à la doc consommatrice). |

**Verdict** : aucun gate violé. F37 est une feature transversale frontend qui n'introduit ni table, ni LLM, ni rôle.

### Contraintes techniques (rappel)

- Stack imposée respectée (Nuxt 4 + Tailwind v4 + gsap, déjà en `package.json`).
- SSR-safe obligatoire : aucun accès `window`/`document` au top-level d'un composant ; isolation des effets dans `onMounted`.
- Hébergement EU/Afrique de l'Ouest : N/A pour du code frontend, mais aucune lib hébergée chez un CDN US-only ne sera ajoutée (toutes les deps cibles sont publiées sur npm).
- Langue : libellés par défaut en français, override via props/slots (FR-022).

## Project Structure

### Documentation (this feature)

```text
specs/037-ui-primitives/
├── plan.md              # ce fichier
├── research.md          # Phase 0 — décisions techniques
├── data-model.md        # Phase 1 — contrats de composants (props/events/slots)
├── quickstart.md        # Phase 1 — comment consommer la lib + lancer la showcase
├── contracts/
│   ├── component-api.md     # convention transverse (size/variant/disabled/events)
│   └── critical-atoms.md    # contrats détaillés des atomes à risque API
│                            # (Button, Input, Number, Select/Combobox/MultiSelect,
│                            #  Modal, Toast, FileUpload)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (sortira de /speckit-tasks)
```

### Source Code (repository root)

```text
frontend/
├── app/
│   ├── components/
│   │   └── ui/                          # 27 atomes auto-importés sous préfixe Ui
│   │       ├── UiButton.vue
│   │       ├── UiInput.vue
│   │       ├── UiTextarea.vue
│   │       ├── UiNumber.vue
│   │       ├── UiSelect.vue
│   │       ├── UiCombobox.vue
│   │       ├── UiMultiSelect.vue
│   │       ├── UiRadioGroup.vue
│   │       ├── UiCheckboxGroup.vue
│   │       ├── UiSwitch.vue
│   │       ├── UiDatePicker.vue
│   │       ├── UiDateRangePicker.vue
│   │       ├── UiSlider.vue
│   │       ├── UiModal.vue
│   │       ├── UiTooltip.vue
│   │       ├── UiPopover.vue
│   │       ├── UiToast.vue
│   │       ├── UiToastHost.vue          # racine d'app, monte la file
│   │       ├── UiCard.vue
│   │       ├── UiBadge.vue
│   │       ├── UiTag.vue
│   │       ├── UiAvatar.vue
│   │       ├── UiEmptyState.vue
│   │       ├── UiSkeleton.vue
│   │       ├── UiSpinner.vue
│   │       ├── UiProgress.vue
│   │       ├── UiFormField.vue
│   │       └── UiFileUpload.vue
│   ├── composables/
│   │   ├── useReducedMotion.ts          # déjà présent
│   │   ├── useFocusTrap.ts              # nouveau — Modal
│   │   ├── useFloating.ts               # nouveau — wrapper @floating-ui/vue
│   │   ├── useToast.ts                  # nouveau — file de toasts
│   │   ├── useFieldId.ts                # nouveau — ids stables a11y
│   │   └── useMoneyFormat.ts            # nouveau — masque FCFA/EUR pour UiNumber
│   ├── utils/
│   │   └── sanitize.ts                  # nouveau — wrapper DOMPurify
│   ├── pages/
│   │   └── dev/
│   │       └── components.vue           # showcase DEV-only (déjà esquissé)
│   └── assets/
│       └── css/
│           └── tokens.css               # vient de F36
└── tests/
    └── unit/
        ├── ui/
        │   ├── UiButton.spec.ts
        │   ├── UiInput.spec.ts
        │   ├── …                        # un .spec.ts par atome
        │   └── UiFileUpload.spec.ts
        └── composables/
            ├── useReducedMotion.spec.ts # déjà présent
            ├── useFocusTrap.spec.ts
            └── useToast.spec.ts
```

**Structure Decision** : convention Nuxt 4 d'auto-imports avec préfixe `Ui` via `frontend/app/components/ui/`. Les tests unitaires vivent à part dans `frontend/tests/unit/ui/` (cohérent avec `useReducedMotion.spec.ts` déjà placé là). Aucun back-end touché ; aucune migration. Les composables transverses dans `composables/` (auto-imports Nuxt) ; les wrappers techniques dans `utils/`.

## Complexity Tracking

> Aucune violation constitutionnelle à justifier.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (aucune) | — | — |
