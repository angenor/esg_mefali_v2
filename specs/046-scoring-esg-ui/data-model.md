# Data Model — F46 Scoring ESG visualisations UI

**Date** : 2026-05-04
**Phase** : 1 (Design)

Ce document liste les **ViewModels UI** dérivés des schémas backend F23/F11/F09 et les **structures internes** (store, composables, helpers) nécessaires à la page `/scoring`. Aucun nouveau modèle de données persisté n'est introduit côté backend ; un seul **schéma de réponse** est ajouté (`ScoreHistoryEntry`/`ScoreHistoryOut` pour l'endpoint history).

---

## 1. Schémas backend ajoutés (Pydantic v2 strict)

### 1.1 `ScoreHistoryEntry`

Localisation : `backend/app/scoring/schemas.py`

| Champ | Type | Contraintes |
|---|---|---|
| `score_calculation_id` | `uuid.UUID` | non null |
| `computed_at` | `datetime` | UTC, ISO-8601 |
| `score_global` | `float \| None` | borné `[0, 100]` côté engine F23 (déjà) ; `None` si calcul incomplet |
| `referentiel_version` | `int` | ≥ 1 |

`model_config = ConfigDict(extra="forbid")`.

### 1.2 `ScoreHistoryOut`

| Champ | Type | Contraintes |
|---|---|---|
| `entity_type` | `Literal["entreprise", "projet"]` | (validé via `_validate_entity_type`) |
| `entity_id` | `uuid.UUID` | non null |
| `referentiel_code` | `str` | code catalogue F09 |
| `entries` | `list[ScoreHistoryEntry]` | trié `computed_at DESC`, taille `≤ limit` |

---

## 2. ViewModels frontend (TypeScript)

Localisation : `frontend/app/lib/scoring-viewmodels.ts` (nouveau ; types co-localisés avec les composables qui les produisent).

### 2.1 `ScoreSummaryVM` (1↔1 avec `ScoreSummaryOut` backend)

```ts
export interface ScoreSummaryVM {
  referentielCode: string
  referentielId: string
  referentielVersion: number
  scoreGlobal: number | null
  scoresByPillar: Record<'E' | 'S' | 'G' | string, number | null>
  coverageRatio: number | null
  computedAt: string // ISO-8601
}
```

### 2.2 `ScoreDetailVM` (1↔1 avec `ScoreDetailOut`)

```ts
export interface CoveredIndicatorVM {
  indicateurId: string
  indicateurCode: string
  pillar: 'E' | 'S' | 'G' | string
  value: unknown // any backend payload — affichage dépend de l'unité
  normalizedValue: number | null
  weight: number
  contribution: number
  sourceId: string
}

export interface MissingIndicatorVM {
  indicateurId: string
  indicateurCode: string
  pillar: 'E' | 'S' | 'G' | string
  reason: string // 'value_source_unmapped' | 'value_absent' | …
}

export interface ScoreDetailVM extends ScoreSummaryVM {
  indicateursCouverts: CoveredIndicatorVM[]
  indicateursManquants: MissingIndicatorVM[]
  sourcesUsed: string[]
}
```

### 2.3 `ScoreHistoryEntryVM` (1↔1 avec `ScoreHistoryEntry` backend)

```ts
export interface ScoreHistoryEntryVM {
  scoreCalculationId: string
  computedAt: string
  scoreGlobal: number | null
  referentielVersion: number
}
```

### 2.4 `PillarBucketVM` (helper `mapIndicateursByPillar`)

```ts
export type PillarCode = 'E' | 'S' | 'G' | string

export interface PillarRowVM {
  indicateurId: string
  indicateurCode: string
  pillar: PillarCode
  status: 'covered' | 'missing'
  scoreContribution: number | null      // null si missing
  weight: number | null                  // null si missing
  normalizedValue: number | null
  rawValue: unknown
  sourceId: string | null
  isSourceRevoked: boolean               // calculé via useSourceFetch
  isEditable: boolean                    // miroir de VALUE_SOURCE_MAP
  reason: string | null                  // pour missing
}

export interface PillarBucketVM {
  pillar: PillarCode
  pillarLabel: string                    // 'Environnement' | 'Social' | 'Gouvernance' | code
  scoreByPillar: number | null           // = ScoreSummaryVM.scoresByPillar[pillar]
  rows: PillarRowVM[]                    // triées par contribution desc, puis missing en queue
}
```

### 2.5 `CompareDatasetVM` (helper `useScoringCompare`)

```ts
export interface CompareSeriesVM {
  referentielCode: string
  referentielVersion: number
  scoreGlobal: number | null
  scoresByPillar: Record<PillarCode, number | null>
}

export interface CompareDatasetVM {
  referentiels: CompareSeriesVM[]        // sélection utilisateur (≤ 5 au MVP)
  pillars: PillarCode[]                   // union ordonnée
}
```

### 2.6 `ScoringSnapshotVM`

```ts
export interface ScoringSnapshotVM {
  active: boolean
  frozenCalculationId: string | null
  frozenSummary: ScoreSummaryVM | null   // construit depuis ScoreHistoryEntryVM + complétion via fetch detail
  frozenAt: string | null                 // = computedAt
}
```

---

## 3. Store Pinia `useScoringStore`

Localisation : `frontend/app/stores/scoring.ts`

### 3.1 État

```ts
interface ScoringStoreState {
  entityType: 'entreprise' | 'projet'
  entityId: string | null

  // par référentiel courant
  currentReferentielCode: string | null

  // caches indexés par referentielCode
  summariesByRef: Map<string, ScoreSummaryVM>          // depuis GET /me/scoring/{entity_type}/{entity_id}
  detailsByRef: Map<string, ScoreDetailVM>             // depuis GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}
  historyByRef: Map<string, ScoreHistoryEntryVM[]>     // depuis GET .../history

  // états par référentiel
  loadingByRef: Map<string, 'idle' | 'loading' | 'success' | 'error'>
  errorByRef: Map<string, string | null>

  // recalcul en cours (un à la fois par référentiel)
  recomputingByRef: Map<string, boolean>

  // édition d'indicateur — file d'attente FIFO (P8 : modifications séquentielles par indicateur_id)
  editingIndicateurIds: Set<string>

  // mode snapshot
  snapshot: ScoringSnapshotVM
}
```

### 3.2 Getters

| Getter | Type | Description |
|---|---|---|
| `currentSummary` | `ScoreSummaryVM \| null` | summary du référentiel courant |
| `currentDetail` | `ScoreDetailVM \| null` | détail du référentiel courant (live) ou figé si `snapshot.active` |
| `currentHistory` | `ScoreHistoryEntryVM[]` | historique du référentiel courant |
| `isLoading` | `boolean` | dérivé de `loadingByRef[currentRef] === 'loading'` |
| `isRecomputing` | `boolean` | dérivé de `recomputingByRef[currentRef]` |
| `isSnapshot` | `boolean` | `snapshot.active` |
| `availableReferentiels` | `string[]` | clés de `summariesByRef` |
| `pillarsBuckets` | `PillarBucketVM[]` | dérive `currentDetail` via `mapIndicateursByPillar` |
| `missingIndicators` | `MissingIndicatorVM[]` | extrait |
| `coveragePercent` | `number` | `coverageRatio * 100` arrondi |

### 3.3 Actions

| Action | Signature | Notes |
|---|---|---|
| `setEntity(type, id)` | `(type, id) => void` | initialisation depuis `useEntrepriseProfile` au mount |
| `loadSummaries()` | `() => Promise<void>` | `GET /me/scoring/{entity}/{id}` → remplit `summariesByRef` |
| `loadDetail(refCode)` | `(refCode) => Promise<void>` | idempotent (cache 60 s) |
| `loadHistory(refCode, limit?)` | `(refCode, limit=12) => Promise<void>` | idempotent (cache 60 s) |
| `setCurrentReferentiel(code)` | `(code) => void` | maj URL via `navigateTo` ; lazy-load detail+history si manquants |
| `recompute(refCode)` | `(refCode) => Promise<void>` | `POST /me/scoring/{entity}/{id}/recompute?referentiel=` ; émet `entity_updated{score_calculation,manual}` ; invalide history |
| `editIndicateur(input)` | `({indicateurId, indicateurCode, newValue, refCode}) => Promise<void>` | (a) PATCH `/me/entreprise` sur le champ mappé, (b) `recompute(refCode)`, (c) émet `entity_updated{indicateur,manual}` puis `{score_calculation,manual}`, (d) push/pop `editingIndicateurIds` |
| `enterSnapshot(calcId)` | `(calcId) => Promise<void>` | charge le summary historique correspondant et active le mode |
| `exitSnapshot()` | `() => void` | repasse au live |
| `onChatEntityUpdated(payload)` | `(p) => void` | invalide detail+history du `currentRef` (et summaries si `entity_type='indicateur'`) |

### 3.4 Invariants

- `editIndicateur` est rejeté immédiatement si `snapshot.active` (assert + toast d'erreur).
- `recompute` est rejeté si déjà `recomputingByRef[refCode] === true` (anti double-clic).
- Toute mutation propre déclenche **uniquement** des invalidations ciblées (jamais un `loadSummaries` global).
- Aucun appel SQL direct ; tout passe par le couche service `services/api/scoring.ts` (à créer dans la phase d'implémentation, en miroir de `services/api/action-plan.ts` F45).

---

## 4. Composables

### 4.1 `useScoring(entityType, entityId)`

- Orchestration : monte le store, appelle `loadSummaries()` au premier mount.
- S'abonne au `useChatEventBus` pour `entity_updated{indicateur|score_calculation}` → `onChatEntityUpdated`.
- Expose : `currentSummary`, `currentDetail`, `pillarsBuckets`, `coveragePercent`, `loading`, `error`, `isSnapshot`, ainsi que les actions `setCurrentReferentiel`, `recompute`.

### 4.2 `useScoringHistory(refCode)`

- Lazy-fetch via `loadHistory(refCode)`.
- Expose : `entries`, `loading`, `error`.

### 4.3 `useScoringCompare()`

- État local `selectedRefs: ref<string[]>` (init avec `[currentRef]`).
- Computed `dataset: CompareDatasetVM` à partir de `summariesByRef`.
- Méthodes `select(code)`, `unselect(code)`, `clear()`.

### 4.4 `useIndicateurEdit(refCode)`

- Encapsule le bottom sheet `<ChatBottomSheet>` + `<ShowForm ask_number>` (F39).
- Méthode `openFor(indicateur: PillarRowVM)` :
  - si `!indicateur.isEditable` → toast d'information + CTA chat (`useChatEventBus.emit('open_chat_for_indicateur', {indicateur_code})`) ; ne pas ouvrir la bottom sheet.
  - si `snapshot.active` → toast « Mode snapshot — sortez du mode pour modifier » ; ne rien ouvrir.
  - sinon → `useChatBottomSheet.open({type: 'ask_number', label, unit, currentValue, min, max, onSubmit})`.
- `onSubmit` appelle `store.editIndicateur(...)`.

---

## 5. Helpers purs

### 5.1 `mapIndicateursByPillar(detail: ScoreDetailVM, sources: SourceMap, editable: Set<string>): PillarBucketVM[]`

- Fusionne `indicateurs_couverts` (status `covered`) et `indicateurs_manquants` (status `missing`).
- Groupe par `pillar`.
- Tri : couverts par contribution desc, puis missing à la fin.
- Calcule `isSourceRevoked` via la map `sources` (issue de `useSourceFetch`).
- Calcule `isEditable` via `editable.has(indicateurCode)`.
- Étiquettes piliers via une const `PILLAR_LABELS_FR = { E: 'Environnement', S: 'Social', G: 'Gouvernance' }` (fallback : code en majuscule).

### 5.2 `scoringEditableIndicateurs.ts`

```ts
export const SCORING_EDITABLE_INDICATEUR_CODES: ReadonlySet<string> = new Set([
  'EFFECTIFS_TOTAL',
  'DEMO_S1',
  'CA_AMOUNT',
  'DEMO_E1',
  'PAYS_SIEGE',
  'GOUVERNANCE_BOARD_INDEPENDENCE',
  'GOUVERNANCE_AUDIT_INTERNE',
  'PRATIQUE_POLITIQUE_RSE',
  'PRATIQUE_BILAN_CARBONE',
  'DEMO_G1',
])

// mapping indicateur_code → champ entreprise (pour PATCH /me/entreprise)
export const SCORING_INDICATEUR_TO_ENTREPRISE_PATH: Readonly<
  Record<string, { field: string; jsonPath?: string; type: 'number' | 'string' | 'boolean' | 'money' }>
> = {
  EFFECTIFS_TOTAL: { field: 'taille_effectifs', type: 'number' },
  DEMO_S1: { field: 'taille_effectifs', type: 'number' },
  CA_AMOUNT: { field: 'taille_ca_amount', type: 'money' },
  DEMO_E1: { field: 'taille_ca_amount', type: 'money' },
  PAYS_SIEGE: { field: 'localisation_siege_pays_iso2', type: 'string' },
  GOUVERNANCE_BOARD_INDEPENDENCE: { field: 'gouvernance_json', jsonPath: 'board_independence', type: 'boolean' },
  GOUVERNANCE_AUDIT_INTERNE: { field: 'gouvernance_json', jsonPath: 'audit_interne', type: 'boolean' },
  PRATIQUE_POLITIQUE_RSE: { field: 'pratiques_actuelles_json', jsonPath: 'politique_rse', type: 'boolean' },
  PRATIQUE_BILAN_CARBONE: { field: 'pratiques_actuelles_json', jsonPath: 'bilan_carbone', type: 'boolean' },
  DEMO_G1: { field: 'gouvernance_json', jsonPath: 'audit_interne', type: 'boolean' },
}
```

**Avertissement** : ce fichier est le miroir manuel de `backend/app/scoring/value_source.py` (`VALUE_SOURCE_MAP`). Toute modification du mapping côté backend DOIT être reflétée ici (rappel dans `tasks.md` + assertion en test unitaire).

---

## 6. Diagramme d'état (mode snapshot)

```text
              enterSnapshot(calcId)
   live ─────────────────────────► snapshot
    ▲                                  │
    │                                  │ exitSnapshot()
    │                                  ▼
    └──────────────────────────────── live

actions disponibles :
  live      : Modifier ✓ | Recalculer ✓ | Comparer ✓ | Drilldown ✓
  snapshot  : Modifier ✗ | Recalculer ✗ | Comparer ✓ (lecture) | Drilldown ✗ (cf. R5)
```

Tout passage `live → snapshot` purge `editingIndicateurIds` (assert) et neutralise `recomputingByRef[currentRef]` côté UI (pas d'annulation backend — le calcul en cours continue côté serveur, mais son résultat ne sera pas exposé tant qu'on est en snapshot).

---

## 7. Relations avec les modèles existants

| Modèle existant | Rôle pour F46 | Modification ? |
|---|---|---|
| `score_calculation` (F23) | source des summaries, details, history | aucune (lecture additionnelle) |
| `referentiel`, `indicateur`, `source` (F09) | catalogue lu via les schémas F23 | aucune |
| `entreprise` (F11) | cible des PATCH d'édition d'indicateur (US4) | aucune (route F11 existante) |
| `audit_log` | trace des PATCH F11 et des INSERT score_calculation | aucune (continuité F23/F11) |
| `account`, `account_user` | RLS via JWT | aucune |

Aucune migration Alembic. Aucun changement de contrainte. Aucune RLS policy nouvelle.
