# Data Model — Plan d'action ESG UI (F45)

Phase 1 — modèle de données **côté UI**. Aucune nouvelle table backend, aucune migration. Cette section documente les ViewModels TypeScript dérivés des schemas Pydantic de F31 et les structures de l'état Pinia.

## 1. Types miroir des schemas backend (F31)

Définis dans `frontend/app/types/actionPlan.ts` (à créer en Phase 2).

```ts
// Aligné sur backend/app/action_plan/enums.py
export type Priority = 'haute' | 'moyenne' | 'basse';
export type StepStatus = 'todo' | 'doing' | 'done' | 'postponed';
export type Category = 'esg' | 'carbone' | 'credit' | 'candidature';
export type Horizon = 6 | 12 | 24;

// Aligné sur backend/app/action_plan/schemas.py — ActionStepRead
export interface ActionStep {
  id: string;                          // UUID
  plan_id: string;                     // UUID
  title: string;                       // 3..200 chars
  description: string | null;
  category: Category;
  priority: Priority;
  horizon_at: string;                  // ISO date YYYY-MM-DD
  status: StepStatus;
  responsible_user_id: string | null;  // UUID
  indicateur_id: string | null;        // UUID — gap source
  source_id: string | null;            // UUID — source du gap
  created_at: string;                  // ISO datetime
  updated_at: string;                  // ISO datetime
}

// Aligné sur ActionPlanRead
export interface ActionPlan {
  id: string;
  account_id: string;
  horizon_months: Horizon;
  version: number;                     // ≥ 1
  score_calculation_id: string | null;
  generated_at: string;                // ISO datetime
  generated_by_user_id: string | null;
  steps: ActionStep[];
}

// Aligné sur ActionStepPatch
export interface ActionStepPatchPayload {
  status?: StepStatus;
  responsible_user_id?: string | null;
}
```

## 2. ViewModels UI

### 2.1 `StepCardViewModel`

Dérivé d'un `ActionStep` par `lib/mapStepToCardViewModel.ts` (helper pur). Exposé à `<StepCard>`.

```ts
export interface StepCardViewModel {
  id: string;
  title: string;
  description: string | null;
  priorityLabel: string;               // i18n (« Haute », « Moyenne », « Basse »)
  priorityTone: 'danger' | 'warning' | 'info';  // pour <UiBadge>
  horizonAt: string;                   // ISO date
  horizonRelative: string;             // i18n (« Dans 4 mois »)
  bucket: TimelineBucket;              // cf. § 2.3
  status: StepStatus;
  statusLabel: string;
  statusTone: 'neutral' | 'progress' | 'success' | 'muted';
  responsibleUserId: string | null;
  responsibleAvatarUrl: string | null; // résolu via cache utilisateurs (au mieux)
  responsibleLabel: string;            // « Non assigné » si null
  indicateurId: string | null;
  sourceLink: { href: string; label: string } | null;
  isLoading: boolean;                  // optimistic update en vol
  error: string | null;                // message rollback si échec
}
```

### 2.2 `TimelineViewModel`

Dérivé du plan complet par `lib/mapPlanToTimelineBuckets.ts`.

```ts
export type TimelineBucket = 'lt3m' | '3to6m' | '6to12m' | '12to24m' | 'unscheduled';

export interface TimelineBucketViewModel {
  bucket: TimelineBucket;
  label: string;                       // i18n (« Moins de 3 mois », « 3 à 6 mois »...)
  rangeStart: string | null;           // ISO date
  rangeEnd: string | null;             // ISO date
  steps: StepCardViewModel[];          // déjà projetés
}

export interface TimelineViewModel {
  generatedAt: string;
  horizonMonths: Horizon;
  buckets: TimelineBucketViewModel[];  // ordre stable : lt3m, 3to6m, 6to12m, 12to24m, unscheduled
}
```

### 2.3 Règles de bucketing

```text
delta_months = round((horizon_at - generated_at) en mois)

delta_months IS NULL                       → 'unscheduled'
delta_months ≤ 3                            → 'lt3m'
3 < delta_months ≤ 6                        → '3to6m'
6 < delta_months ≤ 12                       → '6to12m'
12 < delta_months ≤ 24                      → '12to24m'
delta_months > 24                           → '12to24m'   (cap, étape rare)
```

Le toggle horizon (US6) filtre les buckets visibles selon le tableau :

| Toggle | Buckets visibles |
|---|---|
| `6` | `lt3m`, `3to6m`, `unscheduled` |
| `12` | `lt3m`, `3to6m`, `6to12m`, `unscheduled` |
| `24` (défaut) | `lt3m`, `3to6m`, `6to12m`, `12to24m`, `unscheduled` |

### 2.4 `FiltersViewModel`

```ts
export interface PlanFilters {
  priority: Priority[];                // [] = tous
  status: StepStatus[];                // [] = tous
  horizon: Horizon | null;             // null = pas de filtre temporel actif (= 24)
  responsibleUserId: string | null;    // null = tous
}
```

Sérialisation URL (helper `useActionPlanFilters`) :

```text
?priority=haute,moyenne&status=todo&horizon=12&responsible=<uuid>
```

Une clé absente / valeur invalide → ignorée silencieusement (FR-007).

### 2.5 `CompletionViewModel`

```ts
export interface CompletionStats {
  totalVisible: number;                // après filtre horizon
  doneVisible: number;
  percent: number;                     // round(doneVisible / totalVisible * 100), 0 si totalVisible === 0
  hasData: boolean;                    // false si totalVisible === 0 → afficher état neutre
}
```

## 3. Pinia store — `useActionPlanStore`

```ts
interface ActionPlanState {
  plan: ActionPlan | null;
  loading: boolean;
  error: string | null;
  lastFetchedAt: number | null;        // Date.now() pour cache 60 s
  filters: PlanFilters;
  horizonView: Horizon;                // toggle vue (n'altère pas le plan stocké)
  stepStates: Map<string, {           // état UI par étape
    loading: boolean;
    error: string | null;
    optimisticOverlay: Partial<ActionStep> | null;
  }>;
  pendingMutations: Map<string, Array<ActionStepPatchPayload>>;  // file FIFO par step_id
  regenerating: boolean;
}
```

### 3.1 Getters

- `currentPlan: ActionPlan | null`
- `currentVersion: number | null`
- `visibleSteps: ActionStep[]` — applique `filters` + `horizonView`
- `timelineViewModel: TimelineViewModel | null`
- `completionStats: CompletionStats`
- `responsibleOptions: { id: string; label: string }[]` — déduit des `responsible_user_id` distincts présents dans le plan

### 3.2 Actions

- `fetchPlan(force = false): Promise<void>` — respecte cache 60 s sauf `force=true`.
- `applyOptimisticPatch(stepId: string, patch: ActionStepPatchPayload): Promise<void>` — empile la mutation, applique l'overlay UI, déclenche le PATCH backend, rollback en cas d'erreur, retire de la file à la résolution.
- `openEditSheet(stepId: string): void` — pilote `useChatBottomSheet`.
- `setFilters(next: Partial<PlanFilters>): void` — fusionne avec l'existant, met à jour l'URL.
- `setHorizonView(h: Horizon): void`
- `regenerate(horizon: Horizon): Promise<void>` — pose `regenerating=true`, POST F31, refetch et raz `regenerating`.
- `invalidateStep(stepId: string): Promise<void>` — re-fetch ciblé suite à event chat.

### 3.3 Persistance

- Aucune persistance localStorage (le state est dérivé de l'API).
- Les `filters` sont persistés via l'**URL** seulement (US2).

## 4. Transitions d'état d'une étape

```text
┌──────┐  cocher checkbox       ┌──────┐
│ todo │ ─────────────────────► │ done │
└──────┘                        └──────┘
  │                               │
  │ ouvrir sheet → choix « doing »│ ouvrir sheet → choix « todo »
  ▼                               ▼
┌───────┐  cocher checkbox       ┌──────┐
│ doing │ ─────────────────────► │ done │
└───────┘                        └──────┘
  │
  │ ouvrir sheet → choix « postponed »
  ▼
┌───────────┐
│ postponed │
└───────────┘
```

Règles :
- La checkbox bascule **uniquement** entre `todo` et `done` (interaction rapide).
- Les statuts `doing` et `postponed` ne sont accessibles que via le bottom sheet d'édition (`<EditStatusSheet>`).
- Toute transition envoie un PATCH avec le seul champ `status` (sauf si responsable changé en parallèle dans le sheet).

## 5. Événements EventBus chat

| Event name | Payload | Direction | Effet |
|---|---|---|---|
| `entity_updated` | `{ entity_type: 'action_step', entity_id: string }` | Chat → plan-action | `store.invalidateStep(entity_id)` |
| `entity_updated` | `{ entity_type: 'action_plan', entity_id: string }` | Chat → plan-action | `store.fetchPlan(force=true)` |
| `action_step:locally_updated` | `{ step_id: string, patch: ActionStepPatchPayload }` | plan-action → autres surfaces | Notifie le chat / dashboard d'un changement local |
| `action_plan:regenerated` | `{ plan_id: string, version: number }` | plan-action → autres surfaces | Notifie après régénération réussie |

## 6. Validation côté UI

| Champ | Règle |
|---|---|
| `filters.priority[]` | chaque valeur ∈ {`haute`, `moyenne`, `basse`}, sinon écartée |
| `filters.status[]` | chaque valeur ∈ {`todo`, `doing`, `done`, `postponed`}, sinon écartée |
| `filters.horizon` | ∈ {6, 12, 24}, sinon `null` |
| `filters.responsibleUserId` | UUID v4 syntaxiquement valide, sinon `null` |
| `regenerate.horizon` | doit être ∈ {6, 12, 24} avant envoi (sélecteur radio dans la modale) |
| Patch optimiste | `status` doit être un `StepStatus` valide ; `responsible_user_id` UUID ou null |

Toute valeur invalide est rejetée **avant** l'appel réseau (fail-fast UI).

## 7. Cache et invalidations

| Event | Action |
|---|---|
| Ouverture page si dernière fetch < 60 s | Pas de re-fetch (cache hit) |
| Ouverture page si dernière fetch ≥ 60 s ou jamais | `fetchPlan()` |
| Cocher étape (succès) | Update optimiste appliqué, store met à jour `steps[id]` avec la réponse PATCH |
| Cocher étape (échec) | Rollback overlay + toast erreur |
| Régénération réussie | Remplacement complet du plan, `pendingMutations` vidée, `stepStates` réinitialisée |
| Réception event chat `entity_updated{action_step}` | Re-fetch ciblé via `invalidateStep` |
| Réception event chat `entity_updated{action_plan}` | `fetchPlan(force=true)` |

## 8. Empty states

| Cas | Détection | UI |
|---|---|---|
| Pas de scoring (US7) | `GET /me/action-plan` → 404 ET `GET /me/scoring/calculations/last` → 404 | `<EmptyNoScoring>` avec CTA `/scoring` |
| Plan vide / pas de gaps (US8) | `GET /me/action-plan` → 200 avec `steps.length === 0` (cas limite F31) **OU** scoring sans gaps significatifs | `<EmptyNoGaps>` célébration |
| Filtre trop restrictif | `visibleSteps.length === 0` mais `plan.steps.length > 0` | bandeau « Aucune étape ne correspond à ces filtres » + bouton « Réinitialiser » |

> Note : la logique de détection « scoring vs pas de scoring » dépend de la sémantique exacte de F31 (404 vs 200 vide). À confirmer en Phase 2 lors de la lecture du `service.py` ; le contrat OpenAPI F31 indique 404 sur « aucun plan généré ». Pour distinguer « pas de scoring » vs « pas de gaps », l'UI appellera `GET /me/action-plan` en premier, et seulement en cas de 404 fera un appel léger pour vérifier la présence de scoring (si le backend l'expose).
