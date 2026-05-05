# Phase 1 — Data Model: UI Primitives Library (F37)

Spec : [spec.md](./spec.md) · Plan : [plan.md](./plan.md) · Date : 2026-05-02

> F37 ne crée **aucune entité métier** ni table de base de données. Le « modèle de données » de cette feature est l'ensemble des **contrats de composants** (props/events/slots) que la lib expose. Ce document fige les types ; les détails par atome critique sont dans `contracts/`.

## 1. Types transverses (TypeScript)

```ts
// frontend/app/types/ui.ts (nouveau)

export type UiSize = "sm" | "md" | "lg";
export type UiVariant = "primary" | "secondary" | "ghost" | "danger" | "link";
export type UiSeverity = "info" | "success" | "warning" | "error";

export interface UiOption<V = string | number> {
  value: V;
  label: string;
  disabled?: boolean;
  description?: string;     // pour Combobox
  group?: string;           // pour Select/Combobox
}

export type UiOptionsLoader<V = string | number> = (q: {
  search: string;
  page: number;
  pageSize: number;
}) => Promise<{ items: UiOption<V>[]; total: number }>;

export interface UiToast {
  id: string;
  severity: UiSeverity;
  title?: string;
  message: string;
  duration?: number;        // ms, 0 = persistant
  actionLabel?: string;
  onAction?: () => void;
}

export interface UiUploadFile {
  id: string;
  file: File;
  status: "queued" | "uploading" | "success" | "error";
  progress: number;         // 0..1
  error?: string;
}

export type UiFieldStatus = {
  invalid: boolean;
  errorMessage?: string;
  describedById?: string;
};
```

## 2. Conventions de props (toutes communes — FR-003, FR-004, FR-007)

| Prop | Type | Atomes concernés | Défaut |
|---|---|---|---|
| `size` | `UiSize` | tous les atomes "tailles" | `"md"` |
| `disabled` | `boolean` | tous les atomes interactifs | `false` |
| `readonly` | `boolean` | atomes de saisie | `false` |
| `id` | `string` | tous les atomes interactifs | auto via `useFieldId()` |
| `ariaLabel` | `string` | quand pas de label visible | `undefined` |
| `modelValue` | générique typé | atomes de saisie | propre à l'atome |

`ref` forwarding (FR-007) : tous les atomes exposent `focus()` via `defineExpose`. Pour les composés (Combobox, FileUpload), `focus()` cible le contrôle interne primaire.

## 3. Conventions d'events (FR-005)

- Saisies : `update:modelValue` (v-model), `change` (alias sémantique pour les sélecteurs), `focus`, `blur`.
- Actions : `click`, `submit`.
- Surfaces : `open`, `close`, `dismiss`.
- Listes : `select`, `reach-end` (pagination async).
- Upload : `add`, `remove`, `progress`, `success`, `error`, `retry`.

Aucun event opaque (`@input` brut sans sémantique) accepté — règle de revue.

## 4. Conventions de slots (FR-022)

- `default` : contenu principal.
- `prefix` / `suffix` : icônes ou unités (ex. unité dans `UiNumber`).
- `label` / `helper` / `error` : override des messages par défaut (français).
- `empty` : pour Combobox/MultiSelect (état "Aucun résultat").

## 5. Modèle des 27 atomes (résumé tabulaire)

| Atome | `modelValue` | Variantes / props clés | Events spécifiques | Slots spécifiques | Détail |
|---|---|---|---|---|---|
| `UiButton` | — | `variant`, `loading`, `iconOnly` | `click` | `prefix`, `suffix` | [contracts/ui-button.md](./contracts/ui-button.md) |
| `UiInput` | `string` | `type='text\|email\|password\|search\|tel\|url'` | `update:modelValue`, `change` | `prefix`, `suffix`, `helper`, `error`, `counter` | [contracts/ui-input.md](./contracts/ui-input.md) |
| `UiTextarea` | `string` | `autosize`, `rows`, `maxlength` | `update:modelValue` | `helper`, `error`, `counter` | — |
| `UiNumber` | `number \| null` | `mode='plain'\|'money'`, `currency`, `min`, `max`, `step` | `update:modelValue` | `prefix`, `suffix` | [contracts/ui-number.md](./contracts/ui-number.md) |
| `UiSelect` | `V \| null` | options, `groups`, `clearable` | `update:modelValue`, `change` | `option`, `empty` | [contracts/ui-select-combobox.md](./contracts/ui-select-combobox.md) |
| `UiCombobox` | `V \| null` | `loader?`, `creatable`, recherche locale ou async paginée | `update:modelValue`, `select`, `reach-end` | `option`, `empty` | id |
| `UiMultiSelect` | `V[]` | `creatable`, `maxSelected`, `chipRemovable` | `update:modelValue`, `select`, `remove` | `chip`, `option`, `empty` | id |
| `UiRadioGroup` | `V` | `inline\|stacked` | `update:modelValue` | `option` | — |
| `UiCheckboxGroup` | `V[]` | `inline\|stacked` | `update:modelValue` | `option` | — |
| `UiSwitch` | `boolean` | `labelOn`, `labelOff` | `update:modelValue` | `label-on`, `label-off` | — |
| `UiDatePicker` | `string` ISO `yyyy-mm-dd` | `min`, `max`, locale FR | `update:modelValue` | `helper`, `error` | — |
| `UiDateRangePicker` | `{ start: string; end: string } \| null` | `min`, `max` | `update:modelValue` | `helper`, `error` | — |
| `UiSlider` | `number` ou `[number, number]` | `min`, `max`, `step`, `range` | `update:modelValue`, `change` | `value` | — |
| `UiModal` | `boolean` (open) | `size`, `closeOnOverlay`, `closeOnEsc`, `persistent` | `update:modelValue`, `close`, `open` | `header`, `body`, `footer` | [contracts/ui-modal.md](./contracts/ui-modal.md) |
| `UiTooltip` | — | `placement`, `delay`, `disabled` | `open`, `close` | `default`, `content` | — |
| `UiPopover` | `boolean` (open) | `placement`, `triggerOn='click\|hover\|manual'` | `update:modelValue`, `open`, `close` | `trigger`, `content` | — |
| `UiToast` | — | `severity`, `actionLabel` | `dismiss`, `action` | `default`, `action` | [contracts/ui-toast.md](./contracts/ui-toast.md) |
| `UiToastHost` | — | (singleton) | — | — | host de la file |
| `UiCard` | — | `padded`, `elevation` | — | `header`, `body`, `footer` | — |
| `UiBadge` | — | `severity`, `subtle\|solid` | — | `default` | — |
| `UiTag` | — | `removable` | `remove` | `default` | — |
| `UiAvatar` | — | `shape='circle\|square'`, `src`, fallback initiales | — | — | — |
| `UiEmptyState` | — | `severity`, illustration via slot | `action` | `illustration`, `title`, `description`, `action` | — |
| `UiSkeleton` | — | `shape='line\|rect\|circle'`, `lines`, `width`, `height` | — | — | — |
| `UiSpinner` | — | `label` | — | — | — |
| `UiProgress` | `number` 0..100 | `variant='bar\|circular'`, `indeterminate` | — | — | — |
| `UiFormField` | — (transparent) | `label`, `helper`, `required`, `name` (vee-validate) | `update:modelValue` (transparent) | `default` (input slot props : `id`, `state`, `aria` props) | — |
| `UiFileUpload` | `UiUploadFile[]` | `accept` (MIME), `maxSize`, `multiple`, `mode='dropzone\|button'` | `add`, `remove`, `progress`, `success`, `error`, `retry` | `dropzone`, `item`, `empty` | [contracts/ui-file-upload.md](./contracts/ui-file-upload.md) |

## 6. États visuels normalisés

Chaque atome interactif gère explicitement :

```
default → hover → focus(-visible) → active → disabled
                          ↘ error
                          ↘ loading
```

Règles :
- `focus-visible` est obligatoire (pas `focus` simple) — préserve le confort souris.
- `disabled` : `pointer-events: none` + `aria-disabled="true"` ; contraste réduit mais lisible (token `--color-disabled-fg`).
- `loading` : préserve la dimension du composant (pas de saut), spinner accessible via `aria-busy="true"`, libellé conservé pour les lecteurs d'écran.
- `error` : `aria-invalid="true"` + `aria-describedby` pointant vers le message d'erreur ; bordure `--color-danger-border`.

## 7. Singleton `useToast`

```ts
// frontend/app/composables/useToast.ts
export interface UseToastApi {
  toasts: Readonly<Ref<UiToast[]>>;
  push(t: Omit<UiToast, "id"> & { id?: string }): string; // returns id
  dismiss(id: string): void;
  clear(): void;
}
export function useToast(): UseToastApi;
```

Bornes : 5 toasts visibles max (file FIFO), `auto-dismiss` 5 s par défaut, `severity='error'` est `aria-live="assertive"`, le reste `aria-live="polite"`. `UiToastHost` est monté une fois dans `app.vue`.

## 8. Validation runtime des props

Toutes les props publiques sont typées TypeScript. Les enums (`UiSize`, `UiVariant`, `UiSeverity`) sont déclarés via `defineProps<{ … }>()` + validateurs Vue runtime pour DEV (warn si valeur hors enum). Pas de zod côté props — réservé à VeeValidate via `UiFormField`.
