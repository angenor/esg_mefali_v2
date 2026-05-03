# Contract — Component API Convention (transverse)

Spec : [../spec.md](../spec.md) · Plan : [../plan.md](../plan.md) · Date : 2026-05-02
Réf. : FR-002, FR-003, FR-004, FR-005, FR-007, FR-024.

> Ce document fige les conventions transverses que TOUS les atomes `Ui*` respectent. Les contrats par atome (`ui-button.md`, `ui-input.md`, …) en héritent et n'en redéfinissent que les exceptions.

## 1. Nommage

- Composants : `Ui<NomCapitalisé>.vue` (ex. `UiButton.vue`).
- Auto-import Nuxt 4 sous le préfixe `Ui` — déclaration dans `nuxt.config.ts` non requise (auto via dossier `components/ui/`).
- Composables : `use<Nom>` en camelCase (`useFocusTrap`, `useFloating`, `useToast`).
- Types : `Ui<Nom>` (ex. `UiSize`, `UiOption<V>`).

## 2. Props standard (héritées par défaut)

| Prop | Type | Défaut | Atomes concernés |
|---|---|---|---|
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | atomes "tailles" |
| `disabled` | `boolean` | `false` | atomes interactifs |
| `readonly` | `boolean` | `false` | atomes de saisie |
| `id` | `string` | auto via `useFieldId()` | atomes interactifs |
| `ariaLabel` | `string` | `undefined` | quand pas de label visible |

## 3. Events standard

| Event | Payload | Émis par |
|---|---|---|
| `update:modelValue` | type du `modelValue` | tous les atomes v-model |
| `change` | même type que `modelValue` | sélecteurs (Select, Combobox, Radio…) |
| `focus` / `blur` | `FocusEvent` | atomes de saisie |
| `click` | `MouseEvent` | atomes d'action |
| `submit` | `Event` | formulaires |
| `open` / `close` / `dismiss` | `void` | overlays (Modal, Popover, Toast) |

## 4. Slots standard

- `default` : contenu principal.
- `prefix` / `suffix` : ornement de gauche/droite (icône, unité…).
- `label`, `helper`, `error` : override de texte (français par défaut).
- `empty` : pour les listes (Combobox, MultiSelect).

## 5. Accessibilité (AA)

- Tout atome interactif est atteignable au clavier sans souris.
- `focus-visible` est obligatoire (token `--ring-focus`).
- Cibles tactiles ≥ 44 × 44 px sur viewport ≤ 768 px.
- `disabled` ⇒ `aria-disabled="true"`.
- `loading` ⇒ `aria-busy="true"`.
- `error` ⇒ `aria-invalid="true"` + `aria-describedby` pointant le message.
- Les libellés visibles servent de `<label for>` quand l'atome utilise un input ; sinon `aria-label`.

## 6. Internationalisation

- Libellés par défaut en français (`"Aucun résultat"`, `"Réessayer"`, `"Fichier trop volumineux"`, …).
- Override via slots (`empty`, `error`) ou props (`placeholder`, `actionLabel`).
- Aucun atome ne fait d'hypothèse `direction: ltr` codée en dur (préparation RTL).

## 7. SSR

- Aucun accès `window`/`document` au top-level d'un composant.
- Tout effet DOM (focus trap, gsap, listeners globaux) est encapsulé dans `onMounted` / `onBeforeUnmount`.
- gsap importé dynamiquement (`const { gsap } = await import('gsap')`) dans `onMounted` quand nécessaire.

## 8. Stabilité d'API (FR-024)

- Toute modification d'une prop publique, d'un nom d'event, ou de la signature d'un slot **casse l'API** et déclenche :
  1. mise à jour de ce fichier (`contracts/component-api.md`) et du contract spécifique de l'atome,
  2. note dans `data-model.md`,
  3. PR séparée de migration des consommateurs.
- Les ajouts non-cassants (nouvelle prop optionnelle, nouveau slot facultatif) sont libres.

## 9. Tests obligatoires (par atome)

Cf. `research.md` R-015. Chaque `Ui<Name>.spec.ts` couvre :
1. rendu par défaut,
2. chaque variante de prop publique,
3. chaque event émis,
4. clavier (Tab, Enter/Esc selon pertinence),
5. attributs ARIA pertinents.

## 10. Anti-patterns interdits

- `v-html` brut (utiliser `utils/sanitize.ts`).
- Appel réseau dans un atome (les données viennent du parent).
- Valeurs visuelles en dur (couleur, espacement, rayon, ombre) — passer par les tokens F36.
- Animation ne respectant pas `prefers-reduced-motion`.
- Event opaque (`@input` brut sans nom métier).
