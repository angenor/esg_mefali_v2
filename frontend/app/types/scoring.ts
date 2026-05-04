// F46 T002 — Types miroir backend (F23) + ViewModels UI scoring.
// Cf. specs/046-scoring-esg-ui/data-model.md §1-§2.

// ===== Backend mirrors (F23 schemas + F46 history) =====

export interface ScoreSummaryOut {
  referentiel_code: string
  referentiel_id: string
  referentiel_version: number
  score_global: number | null
  scores_by_pillar: Record<string, number | null>
  coverage_ratio: number | null
  computed_at: string
}

export interface CoveredIndicatorOut {
  indicateur_id: string
  indicateur_code: string
  pillar: string
  value: unknown
  normalized_value: number | null
  weight: number
  contribution: number
  source_id: string
}

export interface MissingIndicatorOut {
  indicateur_id: string
  indicateur_code: string
  pillar: string
  reason: string
}

export interface ScoreDetailOut extends ScoreSummaryOut {
  indicateurs_couverts: CoveredIndicatorOut[]
  indicateurs_manquants: MissingIndicatorOut[]
  sources_used: string[]
}

export interface ScoreListOut {
  entity_type: 'entreprise' | 'projet'
  entity_id: string
  scores: ScoreSummaryOut[]
}

export interface ScoreHistoryEntry {
  score_calculation_id: string
  computed_at: string
  score_global: number | null
  referentiel_version: number
}

export interface ScoreHistoryOut {
  entity_type: 'entreprise' | 'projet'
  entity_id: string
  referentiel_code: string
  entries: ScoreHistoryEntry[]
}

// ===== ViewModels UI =====

export type PillarCode = 'E' | 'S' | 'G' | string

export interface ScoreSummaryVM {
  referentielCode: string
  referentielId: string
  referentielVersion: number
  scoreGlobal: number | null
  scoresByPillar: Record<PillarCode, number | null>
  coverageRatio: number | null
  computedAt: string
}

export interface CoveredIndicatorVM {
  indicateurId: string
  indicateurCode: string
  pillar: PillarCode
  value: unknown
  normalizedValue: number | null
  weight: number
  contribution: number
  sourceId: string
}

export interface MissingIndicatorVM {
  indicateurId: string
  indicateurCode: string
  pillar: PillarCode
  reason: string
}

export interface ScoreDetailVM extends ScoreSummaryVM {
  indicateursCouverts: CoveredIndicatorVM[]
  indicateursManquants: MissingIndicatorVM[]
  sourcesUsed: string[]
}

export interface ScoreHistoryEntryVM {
  scoreCalculationId: string
  computedAt: string
  scoreGlobal: number | null
  referentielVersion: number
}

export interface PillarRowVM {
  indicateurId: string
  indicateurCode: string
  pillar: PillarCode
  status: 'covered' | 'missing'
  scoreContribution: number | null
  weight: number | null
  normalizedValue: number | null
  rawValue: unknown
  sourceId: string | null
  isSourceRevoked: boolean
  isEditable: boolean
  reason: string | null
}

export interface PillarBucketVM {
  pillar: PillarCode
  pillarLabel: string
  scoreByPillar: number | null
  rows: PillarRowVM[]
}

export interface CompareSeriesVM {
  referentielCode: string
  referentielVersion: number
  scoreGlobal: number | null
  scoresByPillar: Record<PillarCode, number | null>
}

export interface CompareDatasetVM {
  referentiels: CompareSeriesVM[]
  pillars: PillarCode[]
}

export interface ScoringSnapshotVM {
  active: boolean
  frozenCalculationId: string | null
  frozenSummary: ScoreSummaryVM | null
  frozenAt: string | null
}
