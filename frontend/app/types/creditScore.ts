/**
 * F48 — Types ViewModel + DTO frontend du credit scoring.
 *
 * Miroir de specs/048-credit-scoring-ui/data-model.md.
 */

// -- Buckets canoniques ------------------------------------------------------

export type SubscoreBucket =
  | 'solidite_financiere'
  | 'performance_operationnelle'
  | 'engagement_esg'
  | 'gouvernance'

export type ClassificationBucket =
  | 'insuffisant'
  | 'a_ameliorer'
  | 'bon'
  | 'excellent'

export type ClassificationColorToken =
  | 'danger'
  | 'warning'
  | 'success'
  | 'success-strong'

export interface ClassificationView {
  bucket: ClassificationBucket
  label: string
  colorToken: ClassificationColorToken
}

// -- DTO backend (miroir Pydantic) -------------------------------------------

export interface CreditFactorOut {
  name: string
  definition: string
  value: number | null
  weight: number
  contribution: number
  source_id: string
  axis: string
}

export interface CreditScoreOut {
  id: string
  entreprise_id: string
  solvabilite: number
  impact_vert: number
  combine: number
  facteurs: CreditFactorOut[]
  methodologie_version: number
  coherence_warning: boolean
  computed_at: string
  subscores: Partial<Record<SubscoreBucket, number | null>> | null
}

export interface ScoreHistoryEntryDTO {
  id: string
  combine: number
  solvabilite: number
  impact_vert: number
  subscores: Partial<Record<SubscoreBucket, number | null>> | null
  methodologie_version: number
  computed_at: string
  coherence_warning: boolean
}

export interface ScoreHistoryOutDTO {
  items: ScoreHistoryEntryDTO[]
}

export type EligibilityStatus = 'eligible' | 'not_eligible' | 'incomplete'

export interface CriterionEvalDTO {
  code: string
  label: string
  threshold: string | null
  actual: string | null
  met: boolean
  blocking: boolean
}

export interface EligibilityBadgeDTO {
  code: string
  label: string
  description: string
  status: EligibilityStatus
  primary_reason: string | null
  criteria: CriterionEvalDTO[]
  matching_offer_query: string
  source_id: string
  version: number
  valid_from: string
  valid_to: string | null
}

export interface EligibilityListDTO {
  items: EligibilityBadgeDTO[]
  evaluated_at: string
  catalog_version_max: number
}

export interface CreditRecommendationDTO {
  step_id: string
  title: string
  description: string | null
  target_subscore: SubscoreBucket
  estimated_credit_points_impact: number
}

export interface CreditRecommendationsDTO {
  items: CreditRecommendationDTO[]
  selected_subscores: SubscoreBucket[]
}

// -- Money payload (P5) ------------------------------------------------------

export interface MoneyValue {
  amount: string
  currency: 'XOF' | 'EUR' | 'USD'
}

export interface CreditDeclarativePayload {
  chiffre_affaires?: MoneyValue
  ebe?: MoneyValue
  dette?: MoneyValue
  fonds_propres?: MoneyValue
}

// -- Frontend ViewModels -----------------------------------------------------

export type SubscoresView = Record<SubscoreBucket, number | null>

export interface CreditScoreView {
  id: string
  combine: number
  combinePrev: number | null
  delta: number | null
  classification: ClassificationView
  subscores: SubscoresView
  partialCoverage: boolean
  computedAt: Date
  methodologieVersion: number
  coherenceWarning: boolean
  solvabilite: number
  impactVert: number
}

export interface HistoryEntry {
  id: string
  combine: number
  computedAt: Date
  methodologieVersion: number
}

export interface EligibilityBadgeView {
  code: string
  label: string
  description: string
  status: EligibilityStatus
  primaryReason: string | null
  criteria: CriterionEvalDTO[]
  matchingOfferQuery: string
  sourceId: string
}

export interface RecommendationView {
  stepId: string
  title: string
  description: string | null
  targetSubscore: SubscoreBucket
  estimatedPointsImpact: number
}
