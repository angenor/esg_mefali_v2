# Contract — Composants & composables F44

**Date** : 2026-05-03
**Status** : Phase 1.

## C-COMP-1 — `WelcomeStrip.vue`

**Path** : `frontend/app/components/dashboard/WelcomeStrip.vue`.
**Props** :

```typescript
interface Props {
  raisonSociale: string                   // résolu depuis useEntrepriseProfile()
  lastDiagnosticAt: Date | null           // = max(scores[*].computed_at)
}
```

**Slots** : aucun.
**Events** : aucun (le bouton "Discuter avec l'IA" est un `<NuxtLink to="/chat">`).
**Comportement** :
- Salutation contextuelle selon l'heure (`Bonjour, …` / `Bonsoir, …`).
- Affichage `Dernier diagnostic : il y a X jours` (relatif via `Intl.RelativeTimeFormat`).
- Si `lastDiagnosticAt == null` : mention "Aucun diagnostic encore".
- Bouton "Discuter avec l'IA" toujours visible, classe `btn-primary`.

---

## C-COMP-2 — `DashboardGrid.vue`

**Path** : `frontend/app/components/dashboard/DashboardGrid.vue`.
**Props** : aucune (utilise les slots).
**Slots** : `default` — reçoit les composants `Card*`.
**Comportement** :
- Grille CSS Tailwind responsive : `grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4`.
- Aucun overflow : `min-w-0` sur les cellules pour permettre la troncature interne des cartes.

---

## C-COMP-3 — Composants `Card*.vue` (pattern commun)

**Paths** : `CardScoring.vue`, `CardCarbon.vue`, `CardCredit.vue`, `CardCandidatures.vue`, `CardRapports.vue`, `CardActionPlan.vue`, `CardIntermediaires.vue`.

**Props communes** :

```typescript
interface CardProps<T> {
  vm: CardVM<T>                           // ViewModel taggué (loading | empty | filled | error)
}
```

**Comportement commun (template)** :

```html
<UiCard :aria-busy="vm.kind === 'loading'">
  <CardSkeleton v-if="vm.kind === 'loading'" />
  <EmptyCardCTA v-else-if="vm.kind === 'empty'" :cta="vm.cta" />
  <CardErrorState v-else-if="vm.kind === 'error'" :message="vm.message" @retry="vm.retry" />
  <component :is="contentComponent" v-else :data="vm.data" />
</UiCard>
```

**Spécificités par carte** :

- **`CardScoring`** : `<VizKPICard>` score global + `<VizRadarChart compact :data="byAxis">` + `<VizSourcePin :count="sourceCount">`. Clic sur la carte → `navigateTo(vm.data.href)`.
- **`CardCarbon`** : `<VizKPICard>` `totalAnnualTco2e` + `<VizLineChart compact :data="trend">`. Si `trend.length === 0`, masquer le graphique sans rendre la carte vide.
- **`CardCredit`** : `<VizGaugeChart :value="combineScore">` + `<UiBadge variant="green">` pour chaque `eligibilityBadges[*]` + warning orange si `coherenceWarning`.
- **`CardCandidatures`** : compteurs en pills + `<ul>` 3 dernières (libellé projet/offre + statut + date relative).
- **`CardRapports`** : 2 sous-blocs visuels — "Rapports récents" (3 liens) + "Attestations actives" (mini-QR cliquables).
- **`CardActionPlan`** : checkbox cliquable par étape (composable `useActionStepToggle`) ; spinner mini pendant le PATCH ; revert visuel sur erreur.
- **`CardIntermediaires`** : `<VizLeafletMap height="160px" :pins="pins" disable-pan>` + lien "Voir tous" → `/matching`.

---

## C-COMP-4 — `EmptyCardCTA.vue`

**Path** : `frontend/app/components/dashboard/EmptyCardCTA.vue`.
**Props** :

```typescript
interface Props {
  cta: { label: string; href: string }
}
```

**Comportement** :
- Affiche un message d'invitation (slot par défaut ou prop `message`) + un `<NuxtLink :to="cta.href">` stylé en bouton secondaire.
- Jamais de "0" sec ou "—" sec rendu — la carte hôte garantit que `kind === 'empty'` n'arrive que si données absentes.

---

## C-COMP-5 — `CardErrorState.vue`

**Path** : `frontend/app/components/dashboard/CardErrorState.vue`.
**Props** : `message: string`.
**Events** : `retry`.
**Comportement** : icône d'erreur + message + bouton "Réessayer". `role="alert"` pour a11y.

---

## C-COMP-6 — `CardSkeleton.vue`

**Path** : `frontend/app/components/dashboard/CardSkeleton.vue`.
**Props** : `lines: number = 3`, `withChart: boolean = false`.
**Comportement** : combinaison de `<UiSkeleton>` (titres + lignes + zone graph optionnelle). Animation `pulse` désactivée si `useReducedMotion()` actif.

---

## C-COMP-7 — `ExportButton.vue`

**Path** : `frontend/app/components/dashboard/ExportButton.vue`.
**Props** : aucune.
**Events** : `exported` (déclenché après download réussi, pour télémétrie future).
**Comportement** :
- `useDataExport().download()` au clic.
- Désactivé pendant requête + 2 s post-download (FR-021).
- Toast "Téléchargement démarré" en succès, "Erreur, réessayez" en échec.

---

## C-CMP-1 — `useDashboardSummary.ts`

**Path** : `frontend/app/composables/useDashboardSummary.ts`.

**API** :

```typescript
interface UseDashboardSummary {
  summary: ComputedRef<DashboardSummaryOut | null>
  loading: ComputedRef<boolean>
  errorByBlock: ComputedRef<Partial<Record<BlockKey, string>>>
  vms: ComputedRef<DashboardCardViewModels>     // dérivé via mapSummaryToCardViewModels
  refresh: (blocks?: BlockKey[]) => Promise<void>
}

function useDashboardSummary(): UseDashboardSummary
```

**Comportement** :
- Au mount : appelle `store.fetchSummary()` ; démarre interval 60 s ; abonne EventBus chat (cf. C-EVT-1).
- À l'unmount : clear interval, désabonne EventBus.
- Visibility API : pause interval si `document.hidden`, reprend (et fetch immédiat) au retour focus.
- `refresh(blocks)` : si `blocks` fourni, n'écrit que ces clés dans le store ; sinon fetch global.

---

## C-CMP-2 — `useDataExport.ts`

**Path** : `frontend/app/composables/useDataExport.ts`.

**API** :

```typescript
interface UseDataExport {
  isDownloading: ComputedRef<boolean>
  download: () => Promise<void>
}

function useDataExport(): UseDataExport
```

**Comportement** :
- Anti double-clic : si `isDownloading`, le second appel est no-op.
- Construit le `Blob` JSON et déclenche le téléchargement programmatique.
- Nom de fichier : `esg-mefali-export-${new Intl.DateTimeFormat('fr-CA').format(new Date())}.json`.

---

## C-CMP-3 — `useDashboardStore` (Pinia)

**Path** : `frontend/app/stores/dashboard.ts`.

**State / Actions** :

```typescript
interface Store {
  state: DashboardState                          // cf. data-model.md
  fetchSummary(opts?: { scope?: BlockKey[] }): Promise<void>
  invalidate(block: BlockKey): void
  reset(): void
}
```

**Règles** :
- `fetchSummary` appelle `GET /me/dashboard/summary`. Si `opts.scope` est fourni, n'écrit que ces clés dans `state.summary` (préserve les autres pour éviter les re-renders).
- `invalidate(block)` ajoute `block` à `state.invalidatedBlocks` ; le prochain `fetchSummary({ scope: [...invalidatedBlocks] })` les consomme.
- `reset()` : utilisé sur logout.

---

## C-EVT-1 — Wiring EventBus chat ↔ dashboard (résumé)

Le détail complet est dans `chat-eventbus-sync.md`. En bref, `useDashboardSummary` s'abonne aux events listés en R5 et appelle `store.invalidate(block)` puis `store.fetchSummary({ scope: [block] })`.

---

## C-LIB-1 — `mapSummaryToCardViewModels.ts`

**Path** : `frontend/app/lib/mapSummaryToCardViewModels.ts`.

**API** :

```typescript
function mapSummaryToCardViewModels(
  summary: DashboardSummaryOut | null,
  options: {
    t: (key: string) => string
    hasProjet: boolean
    isLoading: boolean
    blockErrors: Partial<Record<BlockKey, string>>
    onRetry: (block: BlockKey) => void
  }
): DashboardCardViewModels
```

**Garantie** : fonction **pure**, déterministe, totalement testable sans Vue. Couverture cible : 100 %.
