# Data Model — F44 Dashboard PME UI

**Date** : 2026-05-03
**Status** : Phase 1 — uniquement ViewModels UI dérivés. **Aucune nouvelle entité DB**, **aucune nouvelle table**.

## Entités backend consommées (lecture seule, déjà existantes)

| Entité | Source | Rôle dans F44 |
|--------|--------|---------------|
| `DashboardSummaryOut` | `backend/app/dashboard/schemas.py` (F32) | Schéma JSON renvoyé par `GET /me/dashboard/summary`. Source unique de toutes les données affichées. |
| `DataExportOut` | `backend/app/dashboard/schemas.py` (F32) | Schéma JSON renvoyé par `GET /me/data/export`. Téléchargé tel quel, non parsé côté UI. |
| `ActionStepEntry` | sous-schéma de `DashboardSummaryOut` (`next_actions[*]`) | Étape de plan d'action affichée et mutable. |
| Réponse `PATCH /me/action-plan/steps/{id}` | F31 (`backend/app/action_plan/`) | Confirmation de complétion d'une étape. |

Voir `contracts/frontend-api-consumption.md` pour la forme complète des payloads.

## ViewModels frontend (nouveaux)

Ces structures vivent côté front uniquement (`frontend/app/lib/mapSummaryToCardViewModels.ts`). Elles sont produites par mapping pur depuis `DashboardSummaryOut`.

### `DashboardCardViewModels`

Conteneur principal retourné par l'adapter. Une clé par carte.

```typescript
interface DashboardCardViewModels {
  scoring: ScoringCardVM
  carbon: CarbonCardVM
  credit: CreditCardVM
  candidatures: CandidaturesCardVM
  rapports: RapportsCardVM
  actionPlan: ActionPlanCardVM
  intermediaires: IntermediairesCardVM | null   // null = caché (pas de projet)
}
```

### Discriminant `kind`

Chaque `*CardVM` est une union taggée :

```typescript
type CardVM<TFilled> =
  | { kind: 'loading' }                                   // pendant fetch initial
  | { kind: 'empty'; cta: { label: string; href: string } } // pas de donnée → CTA invitation
  | { kind: 'filled'; data: TFilled }                     // donnée présente
  | { kind: 'error'; message: string; retry: () => void } // échec — bouton réessayer
```

Cette discrimination unique élimine la branchitude `v-if/v-else` dans les composants Vue et facilite les tests unitaires de l'adapter.

### `ScoringCardVM` (carte scores ESG)

```typescript
type ScoringCardVM = CardVM<{
  scoreGlobal: number                  // 0-100, dernière maj toutes référentiels confondus
  byAxis: { e: number; s: number; g: number }   // mini-radar
  referentielCode: string              // ex. 'GCF v2'
  referentielVersion: number
  computedAt: Date
  sourceCount: number                  // nb sources mobilisées (pour <VizSourcePin>)
  href: string                         // → /scoring (F47)
}>
```

**Règles de mapping** :
- `kind = 'empty'` si `summary.scores.length === 0`.
- `kind = 'filled'` si au moins 1 entrée. On retient la **plus récente** (`max(computed_at)`).
- `byAxis` est dérivé via projection backend ou approximation locale (à confirmer en T1 selon ce que F32 renvoie réellement). Si non disponible, fallback : trois axes égaux à `scoreGlobal` avec annotation discrète.

### `CarbonCardVM`

```typescript
type CarbonCardVM = CardVM<{
  totalAnnualTco2e: Decimal            // dernière année
  year: number
  trend: { quarter: string; tco2e: Decimal }[]   // 4 derniers trimestres pour mini-line-chart
  computedAt: Date
  href: string                         // → /carbone (F48)
}>
```

**Règles de mapping** :
- `kind = 'empty'` si `summary.carbon.length === 0`.
- `trend` : si F32 ne fournit pas le détail trimestriel dans `carbon[*]`, le composant peut afficher une mini-area-chart vide avec le seul KPI annuel (placeholder visuel propre). À itérer selon disponibilité réelle.

### `CreditCardVM`

```typescript
type CreditCardVM = CardVM<{
  combineScore: number                 // 0-100 (gauge)
  solvabilite: number
  impactVert: number
  eligibilityBadges: string[]          // ex. ['BOAD', 'SUNREF'] (déduit côté backend ou règle locale)
  coherenceWarning: boolean            // affiché en badge orange si true
  computedAt: Date
  href: string                         // → /credit-score (F49)
}>
```

**Règles de mapping** :
- `kind = 'empty'` si `summary.credit_score == null`.
- `eligibilityBadges` : si non fourni par le backend, dérivation locale simple : `combineScore >= 60 → ['BOAD']`, `>= 75 → +'SUNREF'`. À sourcer côté backend en T+1 si besoin (P1).

### `CandidaturesCardVM`

```typescript
type CandidaturesCardVM = CardVM<{
  countersByStatut: Record<string, number>     // ex. { en_cours: 2, soumise: 1 }
  total: number
  recent: {
    id: string
    projetLabel: string                         // résolu via projets store ou fallback id court
    offreLabel: string                          // idem
    statut: string
    statutLabel: string                         // libellé FR via map
    soumissionAt: Date | null
  }[]                                            // max 3
  href: string                                  // → /candidatures
}>
```

**Règles de mapping** :
- `kind = 'empty'` si `total === 0`.
- `projetLabel` / `offreLabel` : à résoudre via stores existants ; à défaut, afficher l'id raccourci.

### `RapportsCardVM`

```typescript
type RapportsCardVM = CardVM<{
  recentRapports: {
    id: string
    title: string
    referentielsLabel: string                   // joint FR ex. 'GCF · IFC'
    generatedAt: Date
    downloadHref: string                        // → /rapports/{id}.pdf
  }[]                                            // max 3
  activeAttestations: {
    id: string
    publicId: string
    generatedAt: Date
    validUntil: Date
    verifyHref: string                          // → /verify/{publicId}
  }[]                                            // max 2
  href: string                                  // → /rapports
}>
```

**Règles de mapping** :
- `kind = 'empty'` si `recentRapports.length === 0 && activeAttestations.length === 0`.
- `activeAttestations` : filtrer `summary.attestations.recent` où `valid_until > now && revoked_at == null`.

### `ActionPlanCardVM`

```typescript
type ActionPlanCardVM = CardVM<{
  steps: {
    id: string
    title: string
    category: string
    priority: 'haute' | 'moyenne' | 'basse'
    horizonAt: Date
  }[]                                            // max 3
  href: string                                  // → /plan-action (F46)
}>
```

**Règles de mapping** :
- `kind = 'empty'` si `summary.next_actions.length === 0`.
- Tri : `priority = 'haute'` en premier, puis `horizonAt` croissant.
- Mutation : cocher une étape déclenche `PATCH /me/action-plan/steps/{id}` (cf. contracts) puis re-fetch ciblé du bloc `next_actions` ; la 4ᵉ étape monte en position visible.

### `IntermediairesCardVM`

```typescript
type IntermediairesCardVM = CardVM<{
  pins: {
    id: string
    label: string                               // ex. 'BOAD'
    type: 'fond' | 'banque' | 'autre'
    lat: number
    lng: number
  }[]                                            // exactement 3 si dispo
  href: string                                  // → /matching (F53)
}>
```

**Règles de mapping** :
- Source : fetch séparé `/me/matching/recommendations?limit=3` (lazy depuis le composant).
- Composant non monté si la PME n'a pas de projet (garde-fou parent).
- `kind = 'empty'` si la requête réussit mais `pins.length === 0`.
- `kind = 'error'` si la requête échoue (n'affecte pas les autres cartes).

## État du store `useDashboardStore`

```typescript
interface DashboardState {
  summary: DashboardSummaryOut | null            // brut backend
  generatedAt: Date | null                       // timestamp du dernier fetch global
  blockErrors: Partial<Record<BlockKey, string>> // erreur par bloc (FR-020)
  loading: boolean                               // global initial
  invalidatedBlocks: Set<BlockKey>               // marqué par EventBus, déclenche refresh ciblé
}

type BlockKey =
  | 'scores'
  | 'carbon'
  | 'credit_score'
  | 'candidatures'
  | 'rapports'
  | 'attestations'
  | 'next_actions'
```

**Cache** : `summary` est conservé 60 s ; un `refresh()` après ce délai déclenche un fetch. Avant ce délai, `refresh()` n'est exécuté que si `invalidatedBlocks` est non vide ou si l'appel est explicite (clic utilisateur).

**Concurrence** : un seul fetch en cours à la fois (lock sur `loading`) ; les invalidations qui arrivent pendant un fetch sont accumulées et traitées au retour.

## Dérivations et invariants

- **Pas d'état dérivé persistant** : tout ViewModel est recalculé à chaque mise à jour de `summary` via un `computed` (Pinia getter ou Vue computed).
- **Immutabilité** : aucune mutation directe de `summary` côté UI. Les actions de l'utilisateur (cocher étape) déclenchent un PATCH backend puis un re-fetch — pas de patch in-place du store.
- **Money** : tous les champs `Decimal` (`totalAnnualTco2e`, valeurs trimestrielles) restent en `Decimal` (string parsée via `decimal.js`) jusqu'à l'affichage final via `useMoneyFormat`.
- **Dates** : conversion `string ISO 8601 → Date` une seule fois dans l'adapter ; les composants reçoivent `Date`.

## Flux de données complet

```
HTTP GET /me/dashboard/summary  (Pinia useDashboardStore.fetchSummary)
   ↓
DashboardSummaryOut (raw)       ─── stocké tel quel dans store.summary
   ↓
mapSummaryToCardViewModels()    (computed, pur)
   ↓
DashboardCardViewModels         (props des composants Card*)
   ↓
<CardScoring :vm="vms.scoring" /> etc.

Mutations utilisateur :
  CardActionPlan.toggle(stepId)
   → PATCH /me/action-plan/steps/{id}
   → store.invalidate('next_actions')
   → store.fetchSummary({ scope: ['next_actions'] }) (re-fetch)
   → emit chat event 'action_step:completed' via useChatEventBus

Events chat (useChatEventBus) :
  scoring:computed, carbon:computed, ... → store.invalidate(block)
   → store.fetchSummary({ scope: [block] })
```
