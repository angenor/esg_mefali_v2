# F37 — UI Primitives Library

**Phase** : A — Fondations design (UI MVP)
**Modules brainstorm** : transversal — atomes UI réutilisés par toutes les features
**Dépendances** : F36
**Estimation** : 3 jours

## Contexte et objectif

Bibliothèque d'**atomes UI maison** stylés via les tokens F36. Aucune lib UI tierce. Composants headless-friendly : slots, états explicites (loading, disabled, error), events nommés. Inspiration `shadcn/ui` côté Vue : on possède le code, on le lit, on le modifie.

## User Stories (P1 sauf mention)

- **US1 Boutons** — `<UiButton>` variants `primary | secondary | ghost | danger | link`, sizes `sm/md/lg`, `:loading`, `:icon`, focus ring AA.
- **US2 Inputs** — `<UiInput>`, `<UiTextarea>`, `<UiNumber>` (tabular-nums, unit slot, masque FCFA/EUR optionnel). Label flottant, helper, error state, char counter.
- **US3 Select / Combobox / Multi-select** — `<UiSelect>`, `<UiCombobox>` (recherche + virtualisation 100+ items), `<UiMultiSelect>` (chips). Compatible `options_endpoint` async paginé.
- **US4 Radio / Checkbox / Switch** — Tap targets 44 × 44 mobile, focus visible, support clavier complet.
- **US5 Date / DateRange** — `<UiDatePicker>` natif first, fallback custom calendar pour ranges. Locale FR.
- **US6 Slider (P2)** — Range avec valeur affichée, snap step.
- **US7 Modal / Tooltip / Popover / Toast** — `<UiModal>` focus trap, ESC, overlay click. `<UiPopover>` via `@floating-ui/vue`. `<UiToast>` queue stackable, auto-dismiss 5 s, swipe close mobile.
- **US8 Card / Badge / Tag / Avatar / EmptyState** — `<UiCard>` slots header/body/footer. `<UiAvatar>` initiales fallback. `<UiEmptyState>` illu + titre + CTA.
- **US9 Skeleton / Spinner / Progress** — `<UiSkeleton>` shimmer subtil. `<UiProgress>` bar + circular.
- **US10 Form helpers** — `<UiFormField>` (label + input + helper + error), `<UiFieldset>`. Validation via VeeValidate + zod.
- **US11 File upload** — `<UiFileUpload>` drag & drop + click, multi-fichier, preview thumbnails images, progress par fichier, retry, MIME whitelist, taille max. Réutilisé par F39 (`ask_file_upload`) et F50 (documents).

## Exigences fonctionnelles

- **FR-001** : Composants sous `frontend/app/components/ui/Ui<Name>.vue`. Auto-imports Nuxt 4.
- **FR-002** : Chaque composant a un `.test.ts` (vitest + @testing-library/vue) couvrant rendu, props, events, ARIA roles.
- **FR-003** : Props standard : `:size` (sm/md/lg), `:disabled`, `:readonly` quand applicable.
- **FR-004** : Events explicites : `update:modelValue`, `submit`, `change`, `dismiss`, `select`. Aucun `@input` opaque.
- **FR-005** : Aucun composant ne fait de fetch — props/composables fournis par le parent.
- **FR-006** : Page `/dev/components` (DEV only) rend chaque composant en variants avec contrôles.
- **FR-007** : Tous les composants supportent `ref` forwarding (focus programmatique).

## Exigences non-fonctionnelles

- **NFR-001** : Couverture vitest ≥ 80 % sur `components/ui/`.
- **NFR-002** : Aucun `v-html` sauf contenu sanitized DOMPurify.
- **NFR-003** : Animations gsap respectent `useReducedMotion`.
- **NFR-004** : axe-core 0 violation critique sur showcase.

## Composants livrés (~27 fichiers)

`UiButton, UiInput, UiTextarea, UiNumber, UiSelect, UiCombobox, UiMultiSelect, UiRadioGroup, UiCheckboxGroup, UiSwitch, UiDatePicker, UiDateRangePicker, UiSlider, UiModal, UiTooltip, UiPopover, UiToast, UiCard, UiBadge, UiTag, UiAvatar, UiEmptyState, UiSkeleton, UiSpinner, UiProgress, UiFormField, UiFileUpload`.

## Success Criteria

- **SC-001** : `/dev/components` rend les 27 atomes en états variés sans erreur console.
- **SC-002** : Tests vitest 100 % passent, couverture ≥ 80 %.
- **SC-003** : Bundle JS de `/login` reste < 60 kB gzipped après import des primitives utilisées.

## Hors-scope MVP

- Composants charts → F40.
- Composants chat → F41.
- BottomSheet → F39.
- Drag-reorder (TanStack Table) → post-MVP.

## Risques et points de vigilance

- Tentation de réinventer Floating UI : utiliser `@floating-ui/vue`, pas coder le placement à la main.
- A11y : tester VoiceOver sur Modal + Combobox au moins.
- API instabilité : figer les noms de props **avant** d'utiliser la lib dans 50 pages.
