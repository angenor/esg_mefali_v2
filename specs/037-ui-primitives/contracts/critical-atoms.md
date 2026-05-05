# Contracts — Critical Atoms

Spec : [../spec.md](../spec.md) · Plan : [../plan.md](../plan.md) · Convention transverse : [component-api.md](./component-api.md) · Date : 2026-05-02

> Pour chaque atome listé ici (les plus exposés et les plus consommés), on fige props, events, slots, contraintes a11y. Les atomes non listés suivent uniquement la convention transverse + le tableau récapitulatif de `data-model.md`.

---

## UiButton

**Props**

| Prop | Type | Défaut |
|---|---|---|
| `variant` | `'primary' \| 'secondary' \| 'ghost' \| 'danger' \| 'link'` | `'primary'` |
| `size` | `UiSize` | `'md'` |
| `loading` | `boolean` | `false` |
| `disabled` | `boolean` | `false` |
| `iconOnly` | `boolean` | `false` |
| `type` | `'button' \| 'submit' \| 'reset'` | `'button'` |
| `ariaLabel` | `string` | obligatoire si `iconOnly` |

**Events** : `click(MouseEvent)`.
**Slots** : `default` (label), `prefix` (icône), `suffix` (icône).
**A11y** : si `iconOnly`, `ariaLabel` obligatoire ; `loading` ⇒ `aria-busy="true"` ; `disabled` ⇒ `aria-disabled="true"` + `pointer-events: none` ; spinner remplace l'icône `prefix` ou s'insère devant le label, dimension préservée.
**Tests** : 5 variants × (default / disabled / loading) ; click empêché en `disabled` et `loading` ; sizes ; `iconOnly` sans `ariaLabel` ⇒ warning DEV.

---

## UiInput

**Props**

| Prop | Type | Défaut |
|---|---|---|
| `modelValue` | `string` | `''` |
| `type` | `'text' \| 'email' \| 'password' \| 'search' \| 'tel' \| 'url'` | `'text'` |
| `size` | `UiSize` | `'md'` |
| `disabled` / `readonly` | `boolean` | `false` |
| `placeholder` | `string` | `undefined` |
| `maxlength` | `number` | `undefined` |
| `error` | `string` | `undefined` (active l'état error si défini) |
| `helper` | `string` | `undefined` |
| `clearable` | `boolean` | `false` |

**Events** : `update:modelValue(string)`, `change(string)`, `focus(FocusEvent)`, `blur(FocusEvent)`, `clear()` (si `clearable`).
**Slots** : `prefix`, `suffix`, `helper`, `error`, `counter`.
**A11y** : `aria-invalid` si `error` ; `aria-describedby` pointe vers helper et/ou error (`useFieldId`) ; `clearable` rend un bouton avec `ariaLabel="Effacer"`.

---

## UiNumber

**Props**

| Prop | Type | Défaut |
|---|---|---|
| `modelValue` | `number \| null` | `null` |
| `mode` | `'plain' \| 'money'` | `'plain'` |
| `currency` | `'XOF' \| 'EUR' \| 'USD' \| string` | requis si `mode='money'` |
| `locale` | `string` | `'fr-FR'` |
| `min` / `max` / `step` | `number` | `undefined` |
| `precision` | `number` | `0` (XOF) / `2` (EUR/USD) |

**Events** : `update:modelValue(number | null)`, `focus`, `blur`.
**Slots** : `prefix`, `suffix` (override unité affichée).
**A11y** : input natif `inputmode="decimal"` (mobile) ; format affiché en lecture, valeur brute en édition.
**Conformité P5** : ne fait aucun calcul ni conversion ; `Decimal` reste côté parent ; le peg FCFA-EUR de la constitution est appliqué hors de cet atome.

---

## UiSelect / UiCombobox / UiMultiSelect

**Props communes**

| Prop | Type | Défaut |
|---|---|---|
| `options` | `UiOption<V>[]` | `[]` |
| `loader` | `UiOptionsLoader<V>` | `undefined` (Combobox/MultiSelect uniquement) |
| `groups` | `string[]` | `undefined` |
| `placeholder` | `string` | `'Sélectionner…'` |
| `clearable` | `boolean` | `true` |
| `creatable` | `boolean` | `false` (Combobox/MultiSelect) |
| `maxSelected` | `number` | `undefined` (MultiSelect) |
| `pageSize` | `number` | `20` (loader) |

**`modelValue`** : `V | null` (Select/Combobox), `V[]` (MultiSelect).

**Events** : `update:modelValue`, `change`, `select(option)`, `remove(option)` (MultiSelect), `reach-end()` (loader, déclenche page suivante), `search(string)` (Combobox).

**Slots** : `option` (rendu d'une ligne, slot props : `option`, `selected`, `active`), `empty` (état vide), `chip` (MultiSelect).

**A11y** :
- Pattern WAI-ARIA `combobox` (Combobox/MultiSelect) : `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`.
- Listbox ouverte : `role="listbox"`, items `role="option"` + `aria-selected`.
- Navigation : `↑↓` change `aria-activedescendant`, `Enter` sélectionne, `Esc` ferme, `Backspace` retire le dernier chip si input vide (MultiSelect).

**Virtualisation** : si `options.length > 100` et pas de `loader`, rendu fenêtré (cf. R-010).

---

## UiModal

**Props**

| Prop | Type | Défaut |
|---|---|---|
| `modelValue` | `boolean` | `false` |
| `size` | `'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` |
| `closeOnOverlay` | `boolean` | `true` |
| `closeOnEsc` | `boolean` | `true` |
| `persistent` | `boolean` | `false` (alias `closeOnOverlay=false` + `closeOnEsc=false`) |
| `initialFocus` | `string` (selector) | premier focusable |
| `returnFocus` | `boolean` | `true` |

**Events** : `update:modelValue(boolean)`, `open()`, `close()`.
**Slots** : `header`, `body` (default), `footer`.
**A11y** : `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointe le header, `aria-describedby` pointe la body si `description`. Focus trap actif tant qu'ouverte ; `Esc` ferme si autorisé ; restauration du focus à l'élément déclencheur à la fermeture.
**Empilement** : un store interne maintient une pile ; seule la modale au sommet écoute `Esc` et possède le focus trap actif.
**Animations** : open/close gsap (durée `--motion-fast`), court-circuitées via `useReducedMotion`.

---

## UiToast / UiToastHost

**API impérative** : `useToast().push({ severity, message, … })`.

**`UiToast` props**

| Prop | Type | Défaut |
|---|---|---|
| `severity` | `UiSeverity` | `'info'` |
| `title` | `string` | `undefined` |
| `message` | `string` | requis |
| `duration` | `number` (ms) | `5000` (`0` = persistant) |
| `actionLabel` | `string` | `undefined` |

**Events** : `dismiss(id)`, `action(id)`.
**Slots** : `default` (override message), `action`.

**`UiToastHost`** : composant à monter une seule fois (`app.vue`). Place les toasts dans un portail (`Teleport to="body"`). Région ARIA :
- conteneur `role="region"` `aria-label="Notifications"` ;
- `aria-live="assertive"` pour `severity='error'`, `aria-live="polite"` sinon ;
- bouton fermer avec `ariaLabel="Fermer"`.

**Bornes** : 5 toasts visibles max (FIFO). Fermeture swipe horizontal sur viewport tactile (pointer events natifs). Reste visible au-dessus d'une `Modal`.

---

## UiFileUpload

**Props**

| Prop | Type | Défaut |
|---|---|---|
| `modelValue` | `UiUploadFile[]` | `[]` |
| `accept` | `string[]` (MIME) | `['*/*']` |
| `maxSize` | `number` (bytes) | `10 * 1024 * 1024` |
| `multiple` | `boolean` | `true` |
| `mode` | `'dropzone' \| 'button'` | `'dropzone'` |
| `maxFiles` | `number` | `undefined` |
| `uploadFn` | `(f: File, onProgress) => Promise<void>` | `undefined` (sinon le parent gère via events) |

**Events** : `add(files: File[])`, `remove(id)`, `progress(id, ratio)`, `success(id)`, `error(id, message)`, `retry(id)`.

**Slots** : `dropzone` (override visuel zone), `item` (override d'une ligne fichier), `empty`.

**A11y** :
- `<input type="file">` masqué visuellement mais focusable (jamais `display:none`).
- Dropzone : `role="button"` `aria-label="Glisser des fichiers ou cliquer pour sélectionner"`, `tabindex="0"`, Enter/Espace ouvre le picker.
- Item file : `role="listitem"`, message d'erreur `aria-live="polite"`.

**Comportements** :
- MIME hors whitelist ⇒ rejet par fichier avec message ; les autres continuent.
- Dépassement `maxSize` ⇒ rejet par fichier.
- Réseau coupé ⇒ status `error`, bouton "Réessayer" par fichier.
- Drag enter/leave change la classe visuelle ; gsap court-circuité via `useReducedMotion`.
- Aperçu image : `URL.createObjectURL(file)` + `revokeObjectURL` au unmount.

---

## Notes d'implémentation transverses (rappel)

- Tous les atomes ci-dessus ont leur `Ui<Name>.spec.ts` dans `frontend/tests/unit/ui/`.
- Tous consomment `useReducedMotion`, `useFieldId`, `useFocusTrap` (Modal), `useFloating` (Popover/Tooltip/Combobox), `useToast` (UiToastHost), selon pertinence.
- Aucune valeur visuelle en dur — tout passe par les tokens F36 (`var(--color-…)`, `var(--space-…)`, `var(--radius-…)`, `var(--shadow-…)`, `var(--motion-…)`).
