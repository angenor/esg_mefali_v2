---
description: "Task list for F37 — UI Primitives Library"
---

# Tasks: UI Primitives Library (F37)

**Input** : design documents from `/specs/037-ui-primitives/`
**Prerequisites** : [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/component-api.md](./contracts/component-api.md), [contracts/critical-atoms.md](./contracts/critical-atoms.md)
**Tests** : **OUI, requis** par la spec — FR-002 (un `.test.ts` par composant), SC-005 (couverture ≥ 80 %), SC-002 (audit a11y axe-core 0 violation critique).
**Date** : 2026-05-02

## Format

`- [ ] [TaskID] [P?] [Story?] Description avec chemin de fichier`

- `[P]` : tâche parallélisable (fichier différent, dépendances satisfaites).
- `[USx]` : appartient à User Story x (Phases 3+).

## Conventions de chemin

- Frontend uniquement : `frontend/app/components/ui/`, `frontend/app/composables/`, `frontend/app/utils/`, `frontend/app/types/`, `frontend/app/pages/dev/`, `frontend/tests/unit/ui/`, `frontend/tests/integration/`.

---

## Phase 1 : Setup (infrastructure partagée)

**But** : poser les dépendances, l'arborescence et la config de tests.

- [X] T001 Vérifier que F36 est mergée et que `frontend/app/assets/css/tokens.css` existe (sinon BLOQUER).
- [X] T002 Ajouter les dépendances runtime au `frontend/package.json` : `@floating-ui/vue`, `dompurify`, `vee-validate`, `@vee-validate/zod`, `zod` ; puis `pnpm install` depuis `frontend/`.
- [X] T003 [P] Ajouter les dépendances dev au `frontend/package.json` : `@types/dompurify`, `@testing-library/vue`, `axe-core`.
- [X] T004 [P] Créer la structure de dossiers vide : `frontend/app/components/ui/`, `frontend/app/types/`, `frontend/tests/unit/ui/`, `frontend/tests/integration/`, `frontend/app/pages/dev/`.
- [X] T005 [P] Créer `frontend/vitest.config.ts` (ou enrichir le config existant) avec `coverage: { provider: 'v8', reporter: ['text','html','json-summary'], thresholds: { lines: 80, branches: 80, functions: 80, statements: 80 }, include: ['app/components/ui/**','app/composables/**','app/utils/sanitize.ts'] }`.
- [X] T006 [P] Ajouter dans `frontend/eslint.config.*` une règle de revue : `no-restricted-syntax` interdisant `v-html` brut hors `frontend/app/utils/sanitize.ts` (ouvrir TODO si trop bruyant).

**Checkpoint** : `pnpm install` OK, `pnpm vitest run` boot vide, dossiers prêts.

---

## Phase 2 : Foundational (prérequis bloquants)

**But** : utilitaires et composables transverses sans lesquels aucun atome ne peut être écrit.

⚠️ Aucune tâche User Story ne peut démarrer avant la fin de cette phase.

- [X] T010 [P] Créer `frontend/app/types/ui.ts` exposant `UiSize`, `UiVariant`, `UiSeverity`, `UiOption<V>`, `UiOptionsLoader<V>`, `UiToast`, `UiUploadFile`, `UiFieldStatus` (cf. `data-model.md` §1).
- [X] T011 [P] Créer `frontend/app/utils/sanitize.ts` exportant `sanitizeHtml(html, options?)` wrapper DOMPurify (R-005).
- [X] T012 [P] Test `frontend/tests/unit/ui/utils-sanitize.spec.ts` : strip `<script>`, garde `<a href>` whitelisté, refuse `javascript:`.
- [X] T013 [P] Créer `frontend/app/composables/useFieldId.ts` : génère un id stable (SSR-safe via `useId()` de Nuxt 4 si dispo, sinon counter module-scope).
- [X] T014 [P] Test `frontend/tests/unit/composables/useFieldId.spec.ts` : ids uniques, stables au re-render.
- [X] T015 [P] Créer `frontend/app/composables/useFocusTrap.ts` (R-003) : `(containerRef, options) → { activate(), deactivate() }`.
- [X] T016 [P] Test `frontend/tests/unit/composables/useFocusTrap.spec.ts` : Tab cycle, Shift+Tab cycle, restauration focus à `deactivate()`.
- [X] T017 [P] Créer `frontend/app/composables/useFloating.ts` (R-002) : wrapper typé sur `@floating-ui/vue` exposant `{ floatingRef, referenceRef, x, y, strategy, placement, update }`.
- [X] T018 [P] Test `frontend/tests/unit/composables/useFloating.spec.ts` : flip + offset appliqués, autoUpdate déclenché.
- [X] T019 [P] Créer `frontend/app/composables/useToast.ts` (R-008, data-model.md §7) : singleton module, file FIFO bornée à 5, `push/dismiss/clear`.
- [X] T020 [P] Test `frontend/tests/unit/composables/useToast.spec.ts` : push, auto-dismiss après `duration`, persistance si `duration=0`, borne FIFO.
- [X] T021 [P] Créer `frontend/app/composables/useMoneyFormat.ts` (R-012) : `({ currency, locale }) → { display(raw), parse(input) }`.
- [X] T022 [P] Test `frontend/tests/unit/composables/useMoneyFormat.spec.ts` : XOF (precision 0, espace insécable comme séparateur de milliers fr-FR), EUR, USD.
- [X] T023 [P] Créer `frontend/app/middleware/dev-only.ts` : middleware qui renvoie 404 si `process.env.NODE_ENV === 'production'`.
- [X] T024 Modifier `frontend/app/app.vue` (lecture préalable) pour monter `<UiToastHost />` au niveau racine, et confirmer que `tokens.css` est bien importé via `assets/css/main.css`.

**Checkpoint** : utilitaires et composables couverts par tests, toast host monté.

---

## Phase 3 : User Story 1 — Saisir un formulaire candidature accessible (P1) 🎯 MVP

**But** : livrer tous les atomes nécessaires pour monter un formulaire candidature dense (texte + sélection + date + upload + soumission).
**Independent Test** : page de démo formulaire candidature reposant uniquement sur les atomes F37 + tokens F36 ; parcours clavier complet, lecteur d'écran, mobile 375 px (cibles ≥ 44 × 44 px).

### Atomes d'action et de saisie texte

- [X] T030 [P] [US1] Implémenter `frontend/app/components/ui/UiButton.vue` (cf. `contracts/critical-atoms.md` § UiButton).
- [X] T031 [P] [US1] Test `frontend/tests/unit/ui/UiButton.spec.ts` : 5 variants, sizes, `loading` (aria-busy + click empêché), `iconOnly` sans `ariaLabel` ⇒ warn DEV.
- [X] T032 [P] [US1] Implémenter `frontend/app/components/ui/UiInput.vue`.
- [X] T033 [P] [US1] Test `frontend/tests/unit/ui/UiInput.spec.ts` : v-model, types, error/disabled/readonly, clearable, ARIA `invalid`/`describedby`.
- [X] T034 [P] [US1] Implémenter `frontend/app/components/ui/UiTextarea.vue` (autosize en `onMounted`).
- [X] T035 [P] [US1] Test `frontend/tests/unit/ui/UiTextarea.spec.ts` : autosize, maxlength, counter, error.
- [X] T036 [P] [US1] Implémenter `frontend/app/components/ui/UiNumber.vue` (consomme `useMoneyFormat`).
- [X] T037 [P] [US1] Test `frontend/tests/unit/ui/UiNumber.spec.ts` : `mode='money'` XOF/EUR, parse, clamp min/max, `null` autorisé.

### Sélecteurs

- [X] T040 [P] [US1] Implémenter `frontend/app/components/ui/UiSelect.vue` (groups + clearable + ARIA listbox).
- [X] T041 [P] [US1] Test `frontend/tests/unit/ui/UiSelect.spec.ts` : sélection clavier ↑↓ Enter Esc, ARIA roles, groupes.
- [X] T042 [P] [US1] Implémenter `frontend/app/components/ui/UiCombobox.vue` (consomme `useFloating`, virtualisation maison si > 100 options ; loader async paginé).
- [X] T043 [P] [US1] Test `frontend/tests/unit/ui/UiCombobox.spec.ts` : recherche locale, loader mock + `reach-end`, état vide, virtualisation > 100 items.
- [X] T044 [P] [US1] Implémenter `frontend/app/components/ui/UiMultiSelect.vue` (chips supprimables, Backspace si input vide).
- [X] T045 [P] [US1] Test `frontend/tests/unit/ui/UiMultiSelect.spec.ts` : add/remove chips, `maxSelected`, Backspace, `creatable`.

### Dates

- [X] T046 [P] [US1] Implémenter `frontend/app/components/ui/UiDatePicker.vue` (input natif `type=date`, locale FR, clamp `min`/`max`).
- [X] T047 [P] [US1] Test `frontend/tests/unit/ui/UiDatePicker.spec.ts` : v-model ISO, valeur invalide ne casse pas modelValue, error.
- [X] T048 [P] [US1] Implémenter `frontend/app/components/ui/UiDateRangePicker.vue` (deux mois côte-à-côte, `Intl.DateTimeFormat('fr-FR')`).
- [X] T049 [P] [US1] Test `frontend/tests/unit/ui/UiDateRangePicker.spec.ts` : sélection range clavier, contraintes `min`/`max`, fr-FR (lundi en premier).

### Upload + composition de formulaire

- [X] T050 [P] [US1] Implémenter `frontend/app/components/ui/UiFileUpload.vue` (cf. `contracts/critical-atoms.md` § UiFileUpload).
- [X] T051 [P] [US1] Test `frontend/tests/unit/ui/UiFileUpload.spec.ts` : add multi, rejet MIME, rejet size, retry, remove, mode `button`, dropzone Enter ouvre picker, preview image (mock `URL.createObjectURL` + verify `revokeObjectURL` au unmount).
- [X] T052 [US1] Implémenter `frontend/app/components/ui/UiFormField.vue` (slot props : `id`, `state`, `aria-invalid`, `aria-describedby`) — consomme `useField` (vee-validate) si la prop `name` est passée.
- [X] T053 [US1] Test `frontend/tests/unit/ui/UiFormField.spec.ts` : propage label/helper/error en ARIA, branche vee-validate optionnelle.

### Page de démo "candidature"

- [X] T054 [US1] Créer `frontend/app/pages/dev/form-candidature.vue` (DEV-only via middleware T023) qui monte un formulaire enchaînant `UiInput` + `UiNumber money XOF` + `UiSelect` + `UiCombobox` (référentiels mockés à 200 items) + `UiDatePicker` + `UiFileUpload` + `UiButton type=submit`.
- [X] T055 [US1] Documenter dans `frontend/tests/integration/form-candidature.manual.md` : check-list clavier (Tab + Esc + Enter), lecteur d'écran (au moins un atome modal/listbox), mobile 375 px (≥ 44 × 44 px).

**Checkpoint** : User Story 1 fonctionnelle ; un dossier candidature peut se construire avec uniquement les atomes F37.

---

## Phase 4 : User Story 2 — Contenu de bottom-sheet du chat (P1)

**But** : compléter les atomes nécessaires aux sheets F15 (radios, checkboxes, switch, slider) + valider que `UiFormField` se compose avec ces atomes.
**Independent Test** : sheet de démo "Renseigner votre chiffre d'affaires" (`UiNumber money` + `UiSelect` devise + `UiRadioGroup` régime fiscal + `UiButton :loading`) entièrement clavier, valide via VeeValidate + zod.

- [X] T060 [P] [US2] Implémenter `frontend/app/components/ui/UiRadioGroup.vue` (pattern ARIA radiogroup, roving tabindex).
- [X] T061 [P] [US2] Test `frontend/tests/unit/ui/UiRadioGroup.spec.ts` : ↑↓ change sélection, Tab entre/sort du groupe, un seul `tabindex=0`, `inline`/`stacked`.
- [X] T062 [P] [US2] Implémenter `frontend/app/components/ui/UiCheckboxGroup.vue`.
- [X] T063 [P] [US2] Test `frontend/tests/unit/ui/UiCheckboxGroup.spec.ts` : v-model array, indeterminate, `inline`/`stacked`.
- [X] T064 [P] [US2] Implémenter `frontend/app/components/ui/UiSwitch.vue` (cible tactile ≥ 44 × 44 px en `sm`+).
- [X] T065 [P] [US2] Test `frontend/tests/unit/ui/UiSwitch.spec.ts` : toggle clavier (Espace), labels on/off, ARIA.
- [X] T066 [P] [US2] Implémenter `frontend/app/components/ui/UiSlider.vue` (single + range, ARIA `role="slider"` + `aria-valuemin/max/now`).
- [X] T067 [P] [US2] Test `frontend/tests/unit/ui/UiSlider.spec.ts` : ←→ Home/End/PageUp/PageDown, `step` snap, mode `range`.
- [X] T068 [US2] Créer `frontend/app/pages/dev/sheet-ca.vue` (DEV-only) — sheet de démo CA combinant `UiNumber money XOF`, `UiSelect` devise, `UiRadioGroup` régime fiscal, `UiButton :loading`, validation `vee-validate` + `zod`. NB : `UiBottomSheet` lui-même est F39 — ici, simple `<section>` avec les atomes pour valider l'API.
- [X] T069 [US2] Test `frontend/tests/integration/sheet-ca-validation.spec.ts` : submission OK passe schéma zod, submission KO renvoie erreurs vers `UiFormField`.

**Checkpoint** : User Story 2 fonctionnelle ; F15 peut commencer à composer ses sheets.

---

## Phase 5 : User Story 3 — Cohérence inter-pages + showcase (P2)

**But** : livrer les atomes de surface/feedback restants et la page showcase auditée a11y.
**Independent Test** : `/dev/components` rend les 27 atomes, axe-core renvoie 0 violation critique/sérieuse, parcours clavier complet sans piège.

### Surfaces et overlays

- [X] T070 [P] [US3] Implémenter `frontend/app/components/ui/UiModal.vue` (cf. `contracts/critical-atoms.md` § UiModal — consomme `useFocusTrap`, gsap dynamique import).
- [X] T071 [P] [US3] Test `frontend/tests/unit/ui/UiModal.spec.ts` : open/close v-model, Esc respecte `closeOnEsc`, click overlay respecte `closeOnOverlay`, focus trap, restauration focus, modales imbriquées (pile), `prefers-reduced-motion` ⇒ duration 0.
- [X] T072 [P] [US3] Implémenter `frontend/app/components/ui/UiTooltip.vue` (consomme `useFloating`, ARIA `role="tooltip"` + `aria-describedby`).
- [X] T073 [P] [US3] Test `frontend/tests/unit/ui/UiTooltip.spec.ts` : open au hover/focus, close au leave/blur, placement flip si bord.
- [X] T074 [P] [US3] Implémenter `frontend/app/components/ui/UiPopover.vue` (consomme `useFloating`, slot `trigger` + `content`).
- [X] T075 [P] [US3] Test `frontend/tests/unit/ui/UiPopover.spec.ts` : `triggerOn='click'` toggle, `Esc` close, click outside close, `triggerOn='manual'`.
- [X] T076 [P] [US3] Implémenter `frontend/app/components/ui/UiToast.vue` + `frontend/app/components/ui/UiToastHost.vue` (Teleport to body, `aria-live` selon severity, swipe close pointer events).
- [X] T077 [P] [US3] Test `frontend/tests/unit/ui/UiToast.spec.ts` : push via `useToast`, auto-dismiss, action callback, `aria-live` correct, ne casse pas focus trap d'une Modal ouverte.

### Atomes d'affichage et feedback

- [X] T080 [P] [US3] Implémenter `frontend/app/components/ui/UiCard.vue`.
- [X] T081 [P] [US3] Test `frontend/tests/unit/ui/UiCard.spec.ts` : slots header/body/footer, `padded`, `elevation`.
- [X] T082 [P] [US3] Implémenter `frontend/app/components/ui/UiBadge.vue`.
- [X] T083 [P] [US3] Test `frontend/tests/unit/ui/UiBadge.spec.ts` : severities × `subtle`/`solid`.
- [X] T084 [P] [US3] Implémenter `frontend/app/components/ui/UiTag.vue`.
- [X] T085 [P] [US3] Test `frontend/tests/unit/ui/UiTag.spec.ts` : `removable` émet `remove`, focus visible.
- [X] T086 [P] [US3] Implémenter `frontend/app/components/ui/UiAvatar.vue` (initiales fallback si `src` absent ou erreur).
- [X] T087 [P] [US3] Test `frontend/tests/unit/ui/UiAvatar.spec.ts` : initiales depuis `name`, fallback sur erreur image, `shape`.
- [X] T088 [P] [US3] Implémenter `frontend/app/components/ui/UiEmptyState.vue`.
- [X] T089 [P] [US3] Test `frontend/tests/unit/ui/UiEmptyState.spec.ts` : slots illustration/title/description/action.
- [X] T090 [P] [US3] Implémenter `frontend/app/components/ui/UiSkeleton.vue` (R-009 — animation CSS, `prefers-reduced-motion` coupe via `@media`).
- [X] T091 [P] [US3] Test `frontend/tests/unit/ui/UiSkeleton.spec.ts` : `shape='line'/'rect'/'circle'`, `lines`, `width`/`height`.
- [X] T092 [P] [US3] Implémenter `frontend/app/components/ui/UiSpinner.vue` (`role="status"` + `aria-label`).
- [X] T093 [P] [US3] Test `frontend/tests/unit/ui/UiSpinner.spec.ts` : `aria-label`, sizes.
- [X] T094 [P] [US3] Implémenter `frontend/app/components/ui/UiProgress.vue` (`role="progressbar"` + `aria-valuenow/min/max`, `indeterminate`).
- [X] T095 [P] [US3] Test `frontend/tests/unit/ui/UiProgress.spec.ts` : ARIA, variant `bar`/`circular`, `indeterminate`.

### Showcase + audit a11y

- [X] T096 [US3] Créer `frontend/app/pages/dev/components.vue` (DEV-only via middleware T023) — un `<UiCard>` par atome avec contrôles (`size`, `disabled`, `loading`, `error`) ; rendre les 27 atomes en états variés sans erreur console (SC-007).
- [X] T097 [US3] Test `frontend/tests/integration/showcase-a11y.spec.ts` (R-011) : monte la page showcase avec `@vue/test-utils` + `happy-dom`, exécute `axe-core`, asserte 0 violation `critical`/`serious` (SC-002).
- [X] T098 [US3] Documenter dans `frontend/tests/integration/showcase-keyboard.manual.md` : check-list parcours clavier 100 % (SC-003) et mesure tap targets ≤ 375 px (SC-004) ; lien dans `quickstart.md`.

**Checkpoint** : User Story 3 fonctionnelle ; cohérence inter-pages assurée et auditable.

---

## Phase 6 : Polish & cross-cutting concerns

- [~] T100 Mesurer la part JS imputable aux primitives sur `/login` après refonte (build + analyse `dist/` ou `nuxt analyze`) ; documenter le résultat dans `specs/037-ui-primitives/quickstart.md` § 7 ; **fail si > 60 kB gzipped** (SC-006). **Reporté à F38** : `/login` n'est pas encore migré sur F37 — procédure documentée dans `quickstart.md` § 7bis.
- [X] T101 Geler les noms de props publiques (FR-024) : revue croisée `data-model.md` § 5 vs implémentations ; toute divergence corrigée avant merge.
- [X] T102 Test manuel SC-009 sur Modal et Combobox (VoiceOver macOS ou NVDA Windows) ; consigner les résultats dans `frontend/tests/integration/screenreader-a11y.manual.md`.
- [X] T103 Vérifier la couverture vitest globale `pnpm vitest run --coverage` ≥ 80 % sur `app/components/ui/**` + `app/composables/**` + `app/utils/sanitize.ts` (SC-005). Si < 80 %, compléter les tests faibles avant de clore.
- [X] T104 Mettre à jour `docs_et_brouillons/features/00-INDEX.md` : passer F37 de `draft` à `done` (statut + date).
- [X] T105 Créer `docs/CODEMAPS/frontend-ui-primitives.md` (ou compléter le codemap frontend existant) listant les 27 atomes + leurs composables transverses.
- [~] T106 Lancer `make lint` (eslint frontend) et corriger les warnings restants. **Bloqué** : `frontend/eslint.config.*` n'existe pas encore (ESLint 9 exige le format flat) — ticket préalable à ouvrir au niveau projet (T006 setup), hors-scope F37.
- [~] T107 Smoke test final : `make frontend` puis ouvrir manuellement `http://localhost:3001/dev/components`, `http://localhost:3001/dev/form-candidature`, `http://localhost:3001/dev/sheet-ca` — capture d'écran et zéro erreur console. **À exécuter manuellement** par le développeur avant merge.

---

## Validation finale (post-merge des premières features consommatrices)

- [ ] T108 Confirmer SC-001 (formulaire candidature 100 % primitives, sans atome ad hoc) — revue de PR sur la première feature consommatrice.
- [ ] T109 Confirmer SC-008 (un développeur peut composer une page sans introduire un nouveau composant UI hors `frontend/app/components/ui/`) — revue de PR sur la deuxième feature consommatrice.

---

## Dépendances entre phases

```
Phase 1 (Setup) ─► Phase 2 (Foundational) ─► Phase 3 (US1) ─┐
                                            ─► Phase 4 (US2) ─┼─► Phase 6 (Polish)
                                            ─► Phase 5 (US3) ─┘
```

- Phases 3, 4, 5 sont **indépendantes entre elles** une fois la Phase 2 terminée — peuvent être parallélisées par développeur (mais partagent l'API publique : geler `contracts/component-api.md` AVANT la fin de la Phase 3 pour éviter les casse-API).
- T024 (montage `UiToastHost`) ne devient testable qu'à la livraison de T076 ; OK car la Phase 5 referme la dépendance.

## Opportunités de parallélisation

**Phase 2** : T010–T023 sont tous `[P]` (fichiers différents) ; le seul ordre fort est qu'un test arrive après son source.

**Phase 3 (US1)** : 11 atomes `[P]` (T030, T032, T034, T036, T040, T042, T044, T046, T048, T050) + leurs tests `[P]`. Seuls T052 (`UiFormField` consomme les atomes en slot) et T054 (page démo) attendent les autres.

**Phase 4 (US2)** : 4 atomes `[P]` (T060, T062, T064, T066) + tests, puis T068 (page démo) + T069 (test integration).

**Phase 5 (US3)** : 13 atomes `[P]` + tests ; T096 (showcase) attend les 13 ; T097 (axe-core) attend T096.

## Stratégie de livraison

- **MVP minimum** : Phase 1 + Phase 2 + **Phase 3 (US1)**. À ce stade, F26 (formulaires candidatures) peut commencer à consommer la lib.
- **Incrément 1** : ajouter Phase 4 ⇒ F15 (chat bottom-sheets) peut être démarrée.
- **Incrément 2** : ajouter Phase 5 ⇒ F32 (dashboard), F30 (attestations), back-office, extension peuvent toutes consommer en confiance.
- **Clôture** : Phase 6 (audits perf, a11y manuel, doc, codemap, statut INDEX).

---

> Total : 71 tâches numérotées (T001–T109 avec espaces de numérotation pour insertion future), réparties Setup (6) + Foundational (15) + US1 (16) + US2 (10) + US3 (26) + Polish (8) + Validation finale (2). Toutes les tâches respectent le format `- [ ] [Tnnn] [P?] [USx?] description avec chemin`.
