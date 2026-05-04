# Phase 1 — Data Model : Credit scoring UI (F48)

Ce document décrit les **ViewModels UI** consommés par la page `/credit-score` et les **DTO backend** nouveaux/étendus. **Aucune nouvelle table SQL, aucune migration Alembic** — le modèle persistant `credit_score` + `credit_data` de F29 reste inchangé.

## Vue d'ensemble

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  GET /me/credit-score       │ ──────▶ │  CreditScoreOut (étendu)     │
│  GET /me/credit-score/      │         │   ↳ subscores: dict          │
│      history?limit=6        │ ──────▶ │  ScoreHistoryOut             │
│  GET /me/credit-score/      │         │  EligibilityListOut          │
│      eligibility            │ ──────▶ │   ↳ EligibilityBadgeOut[]    │
│  GET /me/credit-score/      │         │  CreditRecommendationsOut    │
│      recommendations        │ ──────▶ │   ↳ CreditRecommendationOut[]│
│  POST /me/credit-data       │ ──────▶ │  CreditDataOut (existant F29)│
│  POST /me/credit-score/     │         │                              │
│      recompute              │ ──────▶ │  CreditScoreOut (étendu)     │
└─────────────────────────────┘         └──────────────────────────────┘
                                                     │
                                                     ▼
                                       ┌─────────────────────────────┐
                                       │  Frontend store + composables│
                                       │  + ViewModels dérivés        │
                                       └─────────────────────────────┘
```

## Backend DTO

### CreditScoreOut — extension `subscores` (F48)

Champ ajouté, **optionnel**, calculé à la volée par le service :

```python
class CreditScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entreprise_id: uuid.UUID
    solvabilite: int = Field(ge=0, le=100)
    impact_vert: int = Field(ge=0, le=100)
    combine: int = Field(ge=0, le=100)
    facteurs: list[dict[str, Any]]
    methodologie_version: int
    coherence_warning: bool
    computed_at: datetime
    # F48 — additif :
    subscores: dict[str, int | None] | None = None  # 4 clés normalisées
```

**Clés `subscores`** : `"solidite_financiere"`, `"performance_operationnelle"`, `"engagement_esg"`, `"gouvernance"`. Valeur ∈ `[0..100]` (entier) ou `None` si aucun facteur du bucket n'a pu être calculé. Champ `null`/absent → l'UI affiche « non calculé » (US2 AS2).

**Calcul** : `compute_subscores(facteurs)` dans `service.py`, lit `subscore_mapping.py` (table déclarative `factor_name → bucket`), pour chaque bucket :

1. Filtre les `facteurs` du bucket.
2. Si vide → `subscores[bucket] = None`.
3. Sinon → moyenne pondérée des `contribution` × poids implicite × normalisation 0-100, arrondie à l'entier.

### ScoreHistoryEntry / ScoreHistoryOut

```python
class ScoreHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: uuid.UUID
    combine: int = Field(ge=0, le=100)
    solvabilite: int = Field(ge=0, le=100)
    impact_vert: int = Field(ge=0, le=100)
    subscores: dict[str, int | None] | None = None
    methodologie_version: int
    computed_at: datetime
    coherence_warning: bool

class ScoreHistoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ScoreHistoryEntry]
```

**Tri** : desc par `computed_at`. **Limite** : `limit ∈ [1..24]` query param, défaut `6`.

### EligibilityBadgeOut / EligibilityListOut

```python
class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    INCOMPLETE = "incomplete"   # un sous-score requis est null

class CriterionEvalOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str                      # "min_combine_score" | "min_subscore_engagement_esg" | …
    label: str                     # libellé FR human-readable
    threshold: str | None          # valeur de référence (ex. "60")
    actual: str | None             # valeur observée pour la PME (ex. "45")
    met: bool                      # critère respecté ou non
    blocking: bool                 # critère qui suffit à refuser

class EligibilityBadgeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str                      # "boad_vert" | "sunref" | "ecobank_green_lending" | …
    label: str                     # nom affiché
    description: str
    status: EligibilityStatus
    primary_reason: str | None     # raison principale si not_eligible/incomplete (clarif Q5)
    criteria: list[CriterionEvalOut]   # exhaustif (clarif Q5)
    matching_offer_query: str      # query string pour /matching (F53)
    source_id: uuid.UUID           # Source verified
    version: int
    valid_from: datetime
    valid_to: datetime | None

class EligibilityListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[EligibilityBadgeOut]
    evaluated_at: datetime
    catalog_version_max: int       # max(version) des dispositifs actifs
```

### CreditRecommendationOut / CreditRecommendationsOut

```python
class CreditRecommendationOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: uuid.UUID                        # → /plan-action#step-{step_id}
    title: str                                # libellé court de l'action
    description: str | None                   # description longue éventuelle
    target_subscore: str                      # "solidite_financiere" | … | "performance_operationnelle"
    estimated_credit_points_impact: int       # déjà filtré >0 et non null par le service

class CreditRecommendationsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CreditRecommendationOut]
    selected_subscores: list[str]             # buckets ciblés par la sélection (info pour UI)
```

**Tri/sélection** côté backend (clarification Q1) : (1) filtre sur sous-scores faibles, (2) tri par `estimated_credit_points_impact` desc, (3) `limit ∈ [1..5]`, défaut `5`.

### Catalogue (interne, pas exposé) — `eligibility_catalog.py`

```python
@dataclass(frozen=True)
class EligibilityRule:
    code: str
    label: str
    description: str
    min_combine_score: int | None
    min_subscore_engagement_esg: int | None
    min_subscore_solidite_financiere: int | None
    excluded_sectors: tuple[str, ...]
    required_min_size: str | None  # "tpe" | "pme" | "eti"
    source_id: UUID
    version: int
    valid_from: datetime
    valid_to: datetime | None
    matching_offer_query: str
```

3 entrées initiales : `boad_vert`, `sunref`, `ecobank_green_lending`. Toutes avec `version=1`, `valid_from` à la date du déploiement, `valid_to=None`. `source_id` pointe vers une `Source` `verified` insérée par migration F09 existante (à valider en implémentation — sinon prévoir un seed dédié dans `backend/scripts/seed_credit_eligibility_sources.py`).

### Mapping interne — `subscore_mapping.py`

```python
SUBSCORE_BUCKETS: tuple[str, ...] = (
    "solidite_financiere",
    "performance_operationnelle",
    "engagement_esg",
    "gouvernance",
)

# factor_name → (bucket, weight_in_bucket)
FACTOR_TO_BUCKET: dict[str, tuple[str, float]] = {
    "ratio_endettement": ("solidite_financiere", 0.35),
    "ratio_liquidite": ("solidite_financiere", 0.25),
    "fonds_propres_ratio": ("solidite_financiere", 0.4),
    "marge_brute": ("performance_operationnelle", 0.4),
    "ebe_ratio": ("performance_operationnelle", 0.4),
    "croissance_ca": ("performance_operationnelle", 0.2),
    # … axe environnementale + sociale → engagement_esg
    # … axe gouvernance → gouvernance
}
```

Liste exacte à compléter à l'implémentation **en lisant les noms de facteurs réels exposés par F29** (via la méthodologie active). La logique de calcul est tolérante : un facteur non mappé est ignoré (le test cas (3) couvre le cas).

## Frontend ViewModels

### `CreditScoreView` (composable `useCreditScore`)

```typescript
type ClassificationBucket = 'insuffisant' | 'a_ameliorer' | 'bon' | 'excellent'

interface CreditScoreView {
  combine: number                    // 0-100, source de vérité pour la gauge
  combinePrev: number | null         // pour delta vs N-1
  delta: number | null               // combine - combinePrev
  classification: {
    bucket: ClassificationBucket
    label: string                    // "Bon"
    colorToken: string               // "success" | "warning" | …
  }
  subscores: {
    solidite_financiere: number | null
    performance_operationnelle: number | null
    engagement_esg: number | null
    gouvernance: number | null
  }
  partialCoverage: boolean           // true si au moins un subscore est null
  computedAt: Date
  methodologieVersion: number
  coherenceWarning: boolean
}
```

### `EligibilityView` (composable `useCreditEligibility`)

```typescript
interface EligibilityView {
  items: Array<{
    code: string
    label: string
    description: string
    status: 'eligible' | 'not_eligible' | 'incomplete'
    primaryReason: string | null
    criteria: Array<{
      code: string
      label: string
      threshold: string | null
      actual: string | null
      met: boolean
      blocking: boolean
    }>
    matchingOfferQuery: string       // → /matching?{matchingOfferQuery}
    sourceId: string                 // pour <VizSourcePin>
  }>
  evaluatedAt: Date
}
```

### `HistoryView` (composable `useCreditHistory`)

```typescript
interface HistoryEntry {
  id: string
  combine: number
  computedAt: Date
  methodologieVersion: number
}

interface HistoryView {
  entries: HistoryEntry[]            // tri desc par computedAt
  current: HistoryEntry | null       // = entries[0]
  previous: HistoryEntry | null      // = entries[1] (pour delta vs N-1)
}
```

### `RecommendationsView` (composable `useCreditScore` ou `useCreditRecommendations`)

```typescript
interface RecommendationView {
  stepId: string                     // pour href "/plan-action#step-{stepId}"
  title: string
  description: string | null
  targetSubscore: keyof CreditScoreView['subscores']
  estimatedPointsImpact: number      // toujours > 0 (cf. backend filtre)
}
```

### `WizardState` (composable `useCreditWizard`, persisté localStorage)

```typescript
type WizardStep = 'financier' | 'esg' | 'gouvernance' | 'recap'

interface WizardState {
  currentStep: WizardStep
  startedAt: Date
  responses: {
    financier?: {
      chiffreAffaires?: { amount: string; currency: string }
      ebe?: { amount: string; currency: string }
      dette?: { amount: string; currency: string }
      fondsPropres?: { amount: string; currency: string }
    }
    esg?: { /* champs collectés */ }
    gouvernance?: { /* champs collectés */ }
  }
}
```

Clé localStorage : `credit-score-wizard-{accountId}-{entrepriseId}`. TTL 7 jours.

### `EditDrawerState` (composable `useCreditEdit`)

```typescript
type EditStep = 'ca' | 'ebe' | 'dette' | 'fonds_propres' | 'recap'

interface EditDrawerState {
  open: boolean
  currentStep: EditStep
  values: WizardState['responses']['financier']
}
```

## Règles de validation UI

| Champ | Règle | Erreur affichée |
|--|--|--|
| `chiffre_affaires.amount` | Decimal > 0 | « Le chiffre d'affaires doit être positif » |
| `chiffre_affaires.currency` | ∈ {XOF, EUR, USD} | « Devise non reconnue » |
| `dette.amount` | Decimal ≥ 0 | « La dette ne peut pas être négative » |
| `fonds_propres.amount` | Decimal ≥ 0 | « Les fonds propres ne peuvent pas être négatifs » |
| `ebe.amount` | Decimal (peut être négatif si perte) | (aucune si format valide) |
| Tous | Format `Money` `{amount: string, currency: string}` | « Format monétaire invalide » |

## Transitions d'état (page)

```
[ Loading ] ──▶ [ HasScore + HasHistory ]
     │              │
     │              ├──▶ [ Editing (drawer) ] ──▶ [ Recomputing ] ──▶ [ HasScore animé ]
     │              ├──▶ [ ViewingEligibility (modal) ]
     │              └──▶ [ NavigatingToPlanAction ]
     │
     ├──▶ [ NoScore ] ──▶ [ Wizard step 1..4 ] ──▶ [ Submitting ] ──▶ [ HasScore ]
     │
     └──▶ [ Error (réseau, 500…) ] ──▶ [ Retry ]
```

États gérés par le store Pinia `useCreditScoreStore`. `Recomputing` ne masque pas la gauge — il anime la transition (R-05).

## Données auditables

Aucune mutation directe introduite par F48. Les écritures restent celles de F29 :

- `submit_credit_data` → audit `entity=credit_data, source_of_change=manual`.
- `recompute_score` → audit `entity=credit_score, source_of_change=manual` (déclenché par UI ou par le service post-`submit_credit_data`).

FR-019 satisfait via les chemins F29 existants — pas de nouvel `audit_log_event_type`.
