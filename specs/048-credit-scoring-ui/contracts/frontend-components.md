# Contract — Frontend components, composables, helpers (F48)

## Page

### `pages/credit-score/index.vue`

- Layout responsive : gauge hero + sous-scores + badges + recommandations + historique + footer méthodologie.
- Branche `useCreditScore` au mount, hydrate le store, écoute EventBus.
- Affiche `<EmptyStateWizard>` si `score == null` ; sinon `<GaugeHero>` + `<SubScoreGrid>` + `<EligibilityBadge>[]` + `<RecommendationList>` + `<ScoreHistoryChart>`.
- Affiche `<PartialCoverageBanner>` si `partialCoverage === true`.

## Composants

### `<GaugeHero>`

Props :

```ts
{
  score: number               // 0-100
  scorePrev: number | null    // pour delta
  classification: ClassificationView
  computedAt: Date
  loading?: boolean
}
```

Émets : `recalc-clicked`. Anime via `animateGaugeTransition(prev, score)` au changement de `score` (watch). Respecte `prefers-reduced-motion`.

### `<ClassificationLabel>`

Props : `{ bucket, label, colorToken }`. Toujours affiche le **libellé textuel** + l'icône **+** la couleur (FR-015 / R-10).

### `<PartialCoverageBanner>`

Props : `{ missing: string[] }` (liste lisible des données manquantes : "Engagement ESG", "Gouvernance"). CTA « Compléter mes données » → ouvre `useCreditEdit` ou le wizard selon contexte.

### `<SubScoreCard>`

Props :

```ts
{
  bucket: 'solidite_financiere' | 'performance_operationnelle' | 'engagement_esg' | 'gouvernance'
  value: number | null   // null → état "non calculé"
  label: string
}
```

État `null` → libellé « non calculé » + CTA « Compléter mes données ».

### `<SubScoreGrid>`

Wrap les 4 `<SubScoreCard>` en grille 2×2 desktop / pile mobile.

### `<EligibilityBadge>`

Props : `{ badge: EligibilityView['items'][number] }`. Affiche : libellé + statut (icône + couleur + texte) + raison principale uniquement (clarif Q5) + pastille `<VizSourcePin>` du `source_id`. Émets `details-clicked` au clic.

### `<EligibilityDetailModal>`

Props : `{ badge, open }`. Émets `update:open`. Contenu : description + tableau exhaustif des `criteria` (label/threshold/actual/met) + bouton « Voir les offres compatibles » ouvrant `/matching?{matching_offer_query}` dans un nouveau routage interne (pas un nouvel onglet — UX fluide).

### `<RecommendationList>` / `<RecommendationCard>`

Liste les `RecommendationView[]`. Chaque carte : titre + description + impact estimé `+{points} points` + mention « estimation » (FR-005). Click → navigation interne `/plan-action#step-{stepId}` (preserve scroll position).

### `<CreditDataDrawer>`

Wrap `<ChatBottomSheet ask_form>` avec un `useCreditEdit` interne. Étapes : CA → EBE → Dette → Fonds propres → Récap. Validation à chaque étape (cf. data-model.md « Règles de validation »).

### `<RecalcStrip>`

Props : `{ computedAt, loading }`. Affiche « Dernier calcul : il y a 3 jours » + bouton « Recalculer maintenant ». Spinner si `loading`.

### `<ScoreHistoryChart>`

Props : `{ entries: HistoryEntry[] }`. Wrap `<VizLineChart>` avec hover : date, valeur, version méthodologie. Si 1 seule entrée → message « Premier calcul ».

### `<EmptyStateWizard>`

Wrap `<ChatBottomSheet show_form>` 4 étapes via `useCreditWizard`. Persistance localStorage automatique. Soumission finale → `POST /me/credit-data` + `POST /me/credit-score/recompute` → bascule vers la vue synthèse.

### `<ExportPdfButton>` (P2)

Désactivé MVP. Affiche infobulle « À venir — F51 ». Reste présent dans le DOM pour test E2E de présence du badge.

## Composables

### `useCreditScore`

```ts
const { score, subscores, classification, partialCoverage, loading, error, refresh } = useCreditScore()
```

Fetch `GET /me/credit-score` + abonnement EventBus `entity_updated{credit_data, credit_score}` → invalidation ciblée.

### `useCreditEligibility`

```ts
const { items, evaluatedAt, loading, error, refresh, byCode } = useCreditEligibility()
```

Cache 60 s. `byCode(code)` retourne le badge ou `undefined`.

### `useCreditHistory`

```ts
const { entries, current, previous, delta, loading, error, refresh } = useCreditHistory({ limit: 6 })
```

Dérive `delta = current.combine - previous.combine` côté composable (pas dans le store).

### `useCreditEdit`

```ts
const { open, currentStep, values, openDrawer, submitStep, submitFinal, cancel, errors } = useCreditEdit()
```

`submitFinal()` orchestre : POST credit-data → POST recompute → store update → emit EventBus.

### `useCreditWizard`

```ts
const { state, currentStep, advance, back, submitFinal, restoreFromStorage, clearStorage } = useCreditWizard()
```

Persistance localStorage automatique à chaque `advance`. `restoreFromStorage()` au mount si TTL valide.

## Helpers purs (testables sans Nuxt)

### `lib/classifyCreditScore.ts`

```ts
export function classify(score: number): {
  bucket: 'insuffisant' | 'a_ameliorer' | 'bon' | 'excellent'
  label: string
  colorToken: 'danger' | 'warning' | 'success' | 'success-strong'
}
```

Implémente les seuils 80/60/40 (clarif Q2). Bornes inférieures inclusives.

### `lib/selectCreditRecommendations.ts`

```ts
export function selectRecommendations(
  raw: CreditRecommendationOut[],
  subscores: SubscoresView,
  limit: number,
): CreditRecommendationOut[]
```

Filet de sécurité côté front si le backend retourne plus que `limit` ou ordre incorrect.

### `lib/animateGaugeTransition.ts`

```ts
export function animateGauge(
  el: SVGElement,
  fromScore: number,
  toScore: number,
  options?: { duration?: number; reducedMotion?: boolean },
): void
```

Tween gsap 320 ms par défaut. Si `reducedMotion`, applique la valeur finale sans animation.

## Store Pinia `useCreditScoreStore`

État :

```ts
{
  score: CreditScoreView | null
  history: HistoryEntry[]
  eligibility: EligibilityBadgeView[]
  recommendations: RecommendationView[]
  loading: { score: boolean; eligibility: boolean; history: boolean; recommendations: boolean }
  error: { score: Error | null; eligibility: Error | null; … }
  computedAt: Date | null
  methodologieVersion: number | null
  wizardState: WizardState | null  // miroir du localStorage
}
```

Actions : `hydrate()`, `refreshAll()`, `refreshScore()`, `refreshEligibility()`, `refreshHistory()`, `refreshRecommendations()`, `applyRecomputeResult(score)`, `setWizardState(state)`, `clearWizard()`.

Getters : `partialCoverage`, `currentClassification`, `delta`, `weakestSubscore`.
