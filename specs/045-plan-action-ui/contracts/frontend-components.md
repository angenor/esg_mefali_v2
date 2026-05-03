# Contract — Frontend components and composables (F45)

Contrats internes des composants Vue 3 et composables nouveaux. Tous les composants suivent le pattern Composition API + `<script setup lang="ts">`.

## Composables

### `useActionPlan()`

**Path** : `frontend/app/composables/useActionPlan.ts`

```ts
export function useActionPlan(): {
  plan: ComputedRef<ActionPlan | null>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string | null>;
  fetchPlan(force?: boolean): Promise<void>;
  invalidateStep(stepId: string): Promise<void>;
};
```

**Responsabilités** :
- Fetch initial `GET /me/action-plan` au mount (respect cache 60 s).
- Souscription `useChatEventBus` à `entity_updated` filtrée sur `entity_type ∈ {'action_step', 'action_plan'}`.
- Désouscription au unmount.
- Re-throw une erreur typée `{ kind: 'no_plan' | 'network' | 'server', cause?: unknown }` pour permettre à la page de différencier les empty states.

### `useActionPlanFilters()`

**Path** : `frontend/app/composables/useActionPlanFilters.ts`

```ts
export function useActionPlanFilters(): {
  filters: ComputedRef<PlanFilters>;
  setFilters(next: Partial<PlanFilters>): void;
  resetFilters(): void;
};
```

**Responsabilités** :
- Lecture initiale des filtres depuis `route.query`, validation, écriture dans le store.
- Synchronisation **bidirectionnelle** : changement de filtre → `router.replace` avec query string ; changement de route (back/forward) → re-application des filtres.
- Validation : valeurs invalides ignorées silencieusement (FR-007).

### `useActionPlanCompletion()`

**Path** : `frontend/app/composables/useActionPlanCompletion.ts`

```ts
export function useActionPlanCompletion(): ComputedRef<CompletionStats>;
```

**Responsabilités** :
- Calcule `done / total / percent` sur le sous-ensemble `visibleSteps` (filtre horizon appliqué, mais **pas** filtres priorité/statut/responsable, qui sont des filtres de **vue liste**, pas des filtres de progression).
- Réactif aux changements de `plan.steps`, `horizonView`, et `stepStates` (overlays optimistes).

### `useActionStepToggle()` (étendu — déjà existant en F44)

**Path** : `frontend/app/composables/useActionStepToggle.ts`

**Extension** : ajout d'une **file d'attente FIFO par step_id**. La signature publique reste compatible :

```ts
export function useActionStepToggle(): {
  toggle(stepId: string, nextStatus: 'todo' | 'done'): Promise<void>;
  isLoading(stepId: string): ComputedRef<boolean>;
  errorOf(stepId: string): ComputedRef<string | null>;
};
```

**Internes** : appuie sur `useActionPlanStore.applyOptimisticPatch`.

## Composants

### `<TimelineHorizontal>`

**Path** : `frontend/app/components/plan-action/TimelineHorizontal.vue`

**Props** :

```ts
interface Props {
  buckets: TimelineBucketViewModel[];
  reducedMotion?: boolean;             // injecté par useReducedMotion
}
```

**Émet** :
- `select-step` `(stepId: string)` — ouvre le sheet d'édition (proxy vers store).

**Comportement** :
- Layout horizontal ≥ 768 px (axe SVG + jalons absolus), vertical < 768 px (axe vertical).
- Stagger gsap 80 ms à l'arrivée (désactivé si `reducedMotion`).
- Tooltip natif (HTML `title` ou `<UiTooltip>` si livré) sur hover/focus → titre de l'étape.

### `<StepCard>`

**Path** : `frontend/app/components/plan-action/StepCard.vue`

**Props** :

```ts
interface Props {
  step: StepCardViewModel;
}
```

**Émet** :
- `toggle-status` `(stepId: string, nextStatus: 'todo' | 'done')`.
- `open-edit` `(stepId: string)`.
- `open-source` `(indicateurId: string)`.

**Comportement** :
- Affiche tous les champs FR-008 ; champs vides → libellé « Non renseigné » discret.
- Checkbox désactivée pendant `step.isLoading` ; spinner localisé.
- Si `step.error`, badge erreur avec retry optionnel.
- a11y : `<article aria-busy>` selon `isLoading` ; bouton « Modifier statut » avec `aria-haspopup="dialog"`.

### `<StepFilters>`

**Path** : `frontend/app/components/plan-action/StepFilters.vue`

**Props** :

```ts
interface Props {
  filters: PlanFilters;
  responsibleOptions: { id: string; label: string }[];
}
```

**Émet** :
- `change` `(next: Partial<PlanFilters>)`.
- `reset` `()`.

**Comportement** :
- Chaque filtre est un `<UiButton>` toggleable (priorité, statut) ou un `<UiSelect>` (responsable). **Tous** vivent dans la barre de filtres elle-même, pas dans un bottom sheet (ce sont des contrôles de vue, pas des inputs de saisie au sens P10 — ils ne créent pas de donnée, ils filtrent une vue ; pattern identique aux filtres de F44).
- Bouton « Réinitialiser » apparaît dès qu'au moins un filtre est actif.

> **Note constitutionnelle P10** : la règle « inputs en bottom sheet » concerne les **inputs de saisie de données** (formulaires, fichiers, sliders qui créent du contenu). Les contrôles de filtre / vue (toggles, dropdowns d'horizon, switches de tri) ne sont pas couverts par P10 : ils ne quittent jamais le client et n'écrivent rien. Pattern précédent : F44 expose ses filtres dashboard en barre.

### `<EditStatusSheet>`

**Path** : `frontend/app/components/plan-action/EditStatusSheet.vue`

**Props** :

```ts
interface Props {
  open: boolean;
  step: ActionStep | null;
  responsibleOptions: { id: string; label: string }[];
}
```

**Émet** :
- `submit` `(payload: ActionStepPatchPayload)`.
- `close` `()`.

**Comportement** :
- Encapsule `<ChatBottomSheet>` (F39) avec `<ShowForm>` (F37 ou créé en F39).
- Champs : `status` (radio group), `responsible_user_id` (select).
- Validation côté UI : au moins un champ modifié sinon `submit` désactivé.
- `Esc` ou clic extérieur → `close` sans submit (FR-012).

### `<RegenerateModal>`

**Path** : `frontend/app/components/plan-action/RegenerateModal.vue`

**Props** :

```ts
interface Props {
  open: boolean;
  defaultHorizon: Horizon;
  busy: boolean;                       // = store.regenerating
}
```

**Émet** :
- `confirm` `(horizon: Horizon)`.
- `cancel` `()`.

**Comportement** :
- Modale (réutilise `<ChatBottomSheet>` mode `display="modal"` ou nouveau `<UiModal>` si livré).
- Avertissement explicite : « Cela créera une nouvelle version. L'ancienne restera consultable dans l'historique. ».
- Sélecteur radio horizon (6 / 12 / 24).
- Bouton « Confirmer » `disabled` si `busy === true`.

### `<HorizonToggle>`

**Path** : `frontend/app/components/plan-action/HorizonToggle.vue`

**Props** :

```ts
interface Props {
  modelValue: Horizon;
}
```

**Émet** :
- `update:modelValue` `(h: Horizon)`.

**Comportement** :
- Trois `<UiButton>` toggleables groupés (`role="tablist"`, a11y conforme).

### `<ProgressHeader>`

**Path** : `frontend/app/components/plan-action/ProgressHeader.vue`

**Props** :

```ts
interface Props {
  stats: CompletionStats;
  version: number;
}
```

**Comportement** :
- Barre de progression `<UiProgressBar>` (F37 si livré, sinon Tailwind).
- KPI texte « X / Y étapes terminées — Z % ».
- Si `stats.hasData === false`, affiche « — » au lieu d'un pourcentage NaN.

### `<EmptyNoScoring>` et `<EmptyNoGaps>`

**Path** : `frontend/app/components/plan-action/EmptyNoScoring.vue` et `EmptyNoGaps.vue`

Encapsulent `<UiEmptyState>` (F37) avec textes et CTA i18n.

### `<HistoryDrawer>` (P2)

**Path** : `frontend/app/components/plan-action/HistoryDrawer.vue`

Différé en P2 ; nécessite un endpoint `GET /me/action-plan/versions` (à ajouter côté F31 si le P2 est livré).

### `<ExportPlanButton>` (P2)

**Path** : `frontend/app/components/plan-action/ExportPlanButton.vue`

Différé derrière flag `PUBLIC_FEATURE_PLAN_EXPORT_PDF`. Dépend de F51.

## Page

### `pages/plan-action/index.vue`

**Layout** : default (réutilise le shell F38).

**Middleware** : `auth` (déjà existant).

**Structure** :

```text
<NuxtPage>
  <h1>{{ t('planAction.title') }}</h1>
  <ProgressHeader v-if="hasPlan" :stats="completion" :version="version" />
  <div class="actions-bar">
    <HorizonToggle v-model="horizonView" />
    <UiButton @click="openRegenerate">{{ t('planAction.regenerate.cta') }}</UiButton>
    <ExportPlanButton v-if="featureFlags.exportPdf" />
    <UiButton variant="ghost" @click="openHistory" v-if="featureFlags.history">
      {{ t('planAction.history.cta') }}
    </UiButton>
  </div>
  <TimelineHorizontal v-if="hasPlan" :buckets="timeline.buckets" @select-step="onSelect" />
  <StepFilters :filters="filters" :responsibleOptions="opts" @change="setFilters" @reset="resetFilters" />
  <ul class="steps-list">
    <StepCard v-for="step in visibleViewModels" :key="step.id" :step="step"
              @toggle-status="onToggle" @open-edit="onEdit" @open-source="onSource" />
  </ul>
  <EmptyNoScoring v-if="emptyKind === 'no_scoring'" />
  <EmptyNoGaps v-if="emptyKind === 'no_gaps'" />
  <NoMatchFilters v-if="emptyKind === 'filtered_out'" @reset="resetFilters" />
  <EditStatusSheet :open="sheetOpen" :step="editingStep" :responsibleOptions="opts"
                   @submit="onSubmitEdit" @close="closeSheet" />
  <RegenerateModal :open="modalOpen" :defaultHorizon="plan?.horizon_months ?? 12"
                   :busy="regenerating" @confirm="onRegenerate" @cancel="closeModal" />
  <HistoryDrawer v-if="featureFlags.history && historyOpen" @close="closeHistory" />
</NuxtPage>
```

## Tests — contrats de test

Chaque composant nouveau a un test `tests/components/plan-action/<Component>.test.ts` qui couvre **a minima** :
- Rendu avec props nominales.
- Émission des events documentés.
- Comportement responsive si pertinent (mobile mock).
- Comportement `prefers-reduced-motion` si animation.
- a11y (rôle, `aria-*`).

Les composables ont `tests/unit/composables/<composable>.test.ts` couvrant :
- Cache 60 s.
- Validation des entrées (filtres, payload patch).
- File d'attente optimistic (concurrence simulée).
- Rollback en cas d'erreur.

## i18n — clés à ajouter dans `frontend/app/locales/fr.ts`

Namespace racine : `planAction`. Sous-clés indicatives (liste exhaustive en Phase 2) :

```text
planAction.title
planAction.subtitle
planAction.regenerate.cta
planAction.regenerate.modal.title
planAction.regenerate.modal.warning
planAction.regenerate.modal.horizonLabel
planAction.regenerate.modal.confirm
planAction.regenerate.modal.cancel
planAction.history.cta
planAction.export.cta
planAction.horizonToggle.label
planAction.horizonToggle.options.6
planAction.horizonToggle.options.12
planAction.horizonToggle.options.24
planAction.filters.priority.label
planAction.filters.priority.haute
planAction.filters.priority.moyenne
planAction.filters.priority.basse
planAction.filters.status.label
planAction.filters.status.todo
planAction.filters.status.doing
planAction.filters.status.done
planAction.filters.status.postponed
planAction.filters.responsible.label
planAction.filters.reset
planAction.progress.label
planAction.progress.units                # « X / Y étapes terminées »
planAction.progress.percent              # « Avancement : Z % »
planAction.empty.noScoring.title
planAction.empty.noScoring.body
planAction.empty.noScoring.cta
planAction.empty.noGaps.title
planAction.empty.noGaps.body
planAction.empty.filteredOut.title
planAction.empty.filteredOut.cta
planAction.card.priorityLabel
planAction.card.horizonRelative          # « Dans {n} mois »
planAction.card.unscheduled              # « Sans échéance »
planAction.card.notAssigned
planAction.card.editStatus
planAction.card.sourceLink
planAction.card.sourceUnavailable
planAction.editSheet.title
planAction.editSheet.statusLabel
planAction.editSheet.responsibleLabel
planAction.editSheet.submit
planAction.editSheet.cancel
planAction.errors.loadFailed
planAction.errors.toggleFailed
planAction.errors.regenerateFailed
planAction.errors.editFailed
```
