# Contracts — UI internal contracts (F51)

Props/events et modèles Pinia consommés par les composants F51.

## Stores Pinia

### `stores/matching.ts`

```ts
state: {
  projetActifId: string | null,         // hydraté depuis useUserStore
  filters: { type, montantMin, montantMax, dureeMin, dureeMax, intermediaireId, secteur, q } // URL-persisted
  offres: OffreMatchItem[],             // résultat /me/projets/{id}/matching ou /me/offres
  loading: boolean,
  error: string | null,
  carteVisible: boolean,
  drawerOffreId: string | null,
}

actions: {
  fetchOffres(),                        // honore projetActifId vs catalogue global
  applyFilters(filters),                // mise à jour + sync URL via useMatchingFilters
  openDrawer(offreId),
  closeDrawer(),
}
```

### `stores/candidatures.ts`

```ts
state: {
  list: CandidatureRow[],
  detail: CandidatureDetail | null,
  draftDirty: boolean,
  saveStatus: 'idle' | 'saving' | 'saved' | 'offline' | 'error',
  saveError: string | null,
  lastSavedAt: number | null,
}

actions: {
  fetchList(),
  fetchDetail(id),
  patchDraft(id, patch, expectedVersion),  // débounce 800 ms via useWizardAutosave
  changeStep(id, newStep),                  // déclenche audit côté serveur
  submit(id, expectedVersion),              // double-confirm
  loadOfflineBuffer(id),                    // hydrate depuis localStorage si présent
}
```

### `stores/simulateur.ts`

```ts
state: {
  inputs: { montant: Money, dureeMois: number, typeInvest: string, partSubventionPct: number },
  results: SimulationResults | null,
  computing: boolean,
  history: SimulationSavedRow[],
  saveSheetOpen: boolean,
}

actions: {
  setInput(key, value),                    // déclenche compute via useSimulateurDebounce
  compute(),                               // POST /me/simulations
  save(label),                             // POST /me/simulations/save
  fetchHistory(),
  delete(id),
  rehydrateFromQuery(query),               // pour /simulateur?montant=&duree= éventuel
}
```

## EventBus (sync chat F41 ↔ wizard, P8)

| Event | Émis par | Consommé par | Payload |
|---|---|---|---|
| `candidature:updated` | wizard step ou submit | `<ChatBottomSheet>` (invalidate context) | `{ candidature_id, version }` |
| `wizard:step:changed` | `useWizardNavigation` | indicateur progression + chat | `{ candidature_id, from, to }` |
| `wizard:document:linked` | `<StepDocuments>` | wizard parent (recalcul progression) | `{ candidature_id, document_id, checklist_key }` |
| `simulateur:saved` | `stores/simulateur.save` | toast + historique refresh | `{ simulation_id, label }` |

## Composants — props/events principaux

### `<OffreCard>`

```vue
defineProps<{ offre: OffreMatchItem }>()
emits: 'click', 'add-to-comparator'
```

Affiche : nom intermédiaire, montant min-max formatté, type, durée, score (si présent).

### `<FiltresPanel>`

```vue
defineProps<{ modelValue: MatchingFilters }>()
emits: 'update:modelValue', 'reset'
```

Form bottom-sheet sur mobile, panneau latéral sur desktop. Synchronise via `v-model`.

### `<CompareTable>` (`pages/matching/compare.vue`)

```vue
defineProps<{ offreIds: string[] }>()
```

Hydrate depuis `useComparateur()` localStorage. Limite 3.

### `<Wizard>` (parent)

```vue
defineProps<{ candidatureId: string }>()
```

Slots `step1..step5`. Transition gsap entre étapes. Indicateur de progression sticky top.

### `<StepDocuments>`

Embed `<ProjetDocumentsGrid>` (F50) avec mode `checklist=offre.documents_requis`. Émet `wizard:document:linked` à chaque (dé)liaison.

### `<StepReponsesLibres>`

Embed `<ChatBottomSheet>` (F41) en mode contextualisé `{ candidature_id, projet_id, offre_id }`. Toute saisie complexe (radios, date, slider) initiée par le chat passe **forcément** par bottom sheet F39 (P10).

### `<SubmissionModal>`

```vue
defineProps<{ candidatureId: string, version: number }>()
emits: 'confirmed', 'cancelled'
```

Modale 2 étapes : (1) lecture avertissement intangibilité, (2) checkbox `userAcknowledgedIntangible` + bouton « Soumettre définitivement » désactivé tant que checkbox non cochée. À la confirmation, appelle `stores/candidatures.submit(id, version)`.

### `<SliderPanel>` simulateur

```vue
defineProps<{ modelValue: SimulateurInputs }>()
emits: 'update:modelValue'
```

4 sliders + sélecteurs dérivés. `v-model` lié à `stores/simulateur.inputs` ; `useSimulateurDebounce(300)` déclenche `compute` automatiquement.

### `<ResultsCharts>` simulateur

```vue
defineProps<{ results: SimulationResults }>()
```

Layout 3 charts F40. Skeleton si `results === null` ; `opacity-70` durant `computing` mais garde dernières données (research §9).

### `<SaveSimulationSheet>`

Bottom sheet F39 demandant un `label` (1..120 chars). À la confirmation, appelle `stores/simulateur.save(label)`.

## Types TS partagés

```ts
type Money = { amount: string; currency: 'XOF' | 'EUR' };

type OffreMatchItem = {
  offre_id: string;
  score?: number;
  rang?: number;
  nom: string;
  intermediaire: { id: string; nom: string; geolocation: { lat: number; lng: number } | null };
  type: 'credit' | 'subvention' | 'garantie' | 'autre';
  montant_min: Money;
  montant_max: Money;
  duree_min_mois: number;
  duree_max_mois: number;
  secteurs: string[];
};

type CandidatureRow = {
  id: string;
  offre_nom: string;
  projet_titre: string;
  statut: 'brouillon' | 'soumise' | 'en_revue' | 'acceptee' | 'refusee';
  step_courant: number;
  progression_pct: number;
  updated_at: string;
  submitted_at: string | null;
};

type SimulationResults = {
  mensualites: { mois: number; amount: string; currency: 'XOF' | 'EUR' }[];
  cout_total: Money;
  economie_estimee: Money;
  co2_evite_t: string;
  decomposition_pct: { principal: number; interets: number; subvention: number };
  formula_refs: { formula_id: string; version: string }[];
};
```

## Util `formatMoney(money, locale='fr-FR')`

Référence research §12. Utilisé dans toutes les vues affichant un `Money`.

## Hooks d'accessibilité (a11y)

- `<OffreCard>` : `role="button"`, focus visible, `aria-label` complet.
- `<CompareTable>` : `<table>` HTML sémantique avec `<caption>` et `<th scope>`.
- `<SliderPanel>` : chaque slider `role="slider"` natif `<input type="range">` avec `aria-valuetext` (e.g. « 150 000 EUR »).
- `<SubmissionModal>` : `role="alertdialog"`, focus trap, ESC ignoré tant que pas confirmé.
- Charts F40 : `aria-label` résumant le chart + `aria-describedby` pointant vers tableau caché.
