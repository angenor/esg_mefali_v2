/**
 * F48 — Store Pinia useCreditScoreStore.
 *
 * Cf. specs/048-credit-scoring-ui/data-model.md + frontend-components.md.
 * État cloisonné par tenant (JWT côté backend). Cache léger sur eligibility
 * et history (60 s) ; score invalidé sur mutation (recompute / EventBus).
 */

import { defineStore } from 'pinia'
import { creditScoreApi } from '~/services/api/creditScore'
import { classifyCreditScore } from '~/lib/classifyCreditScore'
import { selectCreditRecommendations } from '~/lib/selectCreditRecommendations'
import type {
  CreditScoreOut,
  CreditScoreView,
  EligibilityBadgeView,
  EligibilityListDTO,
  HistoryEntry,
  RecommendationView,
  ScoreHistoryEntryDTO,
  ScoreHistoryOutDTO,
  SubscoreBucket,
  SubscoresView,
} from '~/types/creditScore'

const CACHE_TTL_MS = 60_000
const SUBSCORE_KEYS: SubscoreBucket[] = [
  'solidite_financiere',
  'performance_operationnelle',
  'engagement_esg',
  'gouvernance',
]

interface LoadingFlags {
  score: boolean
  history: boolean
  eligibility: boolean
  recommendations: boolean
}

interface ErrorFlags {
  score: string | null
  history: string | null
  eligibility: string | null
  recommendations: string | null
}

interface CreditScoreStoreState {
  rawScore: CreditScoreOut | null
  history: HistoryEntry[]
  historyLoadedAt: number | null
  eligibility: EligibilityBadgeView[]
  eligibilityLoadedAt: number | null
  recommendations: RecommendationView[]
  recommendationsLoadedAt: number | null
  loading: LoadingFlags
  error: ErrorFlags
}

function emptySubscores(): SubscoresView {
  return {
    solidite_financiere: null,
    performance_operationnelle: null,
    engagement_esg: null,
    gouvernance: null,
  }
}

function normaliseSubscores(
  raw: Partial<Record<SubscoreBucket, number | null>> | null,
): SubscoresView {
  const out = emptySubscores()
  if (!raw) return out
  for (const k of SUBSCORE_KEYS) {
    const v = raw[k]
    out[k] = typeof v === 'number' ? v : null
  }
  return out
}

function toHistoryEntry(dto: ScoreHistoryEntryDTO): HistoryEntry {
  return {
    id: dto.id,
    combine: dto.combine,
    computedAt: new Date(dto.computed_at),
    methodologieVersion: dto.methodologie_version,
  }
}

function errMessage(e: unknown): string {
  if (e instanceof Error) return e.message
  return 'Erreur inconnue'
}

export const useCreditScoreStore = defineStore('creditScore', {
  state: (): CreditScoreStoreState => ({
    rawScore: null,
    history: [],
    historyLoadedAt: null,
    eligibility: [],
    eligibilityLoadedAt: null,
    recommendations: [],
    recommendationsLoadedAt: null,
    loading: {
      score: false,
      history: false,
      eligibility: false,
      recommendations: false,
    },
    error: {
      score: null,
      history: null,
      eligibility: null,
      recommendations: null,
    },
  }),
  getters: {
    score(state): CreditScoreView | null {
      if (!state.rawScore) return null
      const subscores = normaliseSubscores(state.rawScore.subscores)
      const partial = SUBSCORE_KEYS.some((k) => subscores[k] === null)
      const previous = state.history[1] ?? null
      const combinePrev = previous?.combine ?? null
      return {
        id: state.rawScore.id,
        combine: state.rawScore.combine,
        combinePrev,
        delta: combinePrev !== null ? state.rawScore.combine - combinePrev : null,
        classification: classifyCreditScore(state.rawScore.combine),
        subscores,
        partialCoverage: partial,
        computedAt: new Date(state.rawScore.computed_at),
        methodologieVersion: state.rawScore.methodologie_version,
        coherenceWarning: state.rawScore.coherence_warning,
        solvabilite: state.rawScore.solvabilite,
        impactVert: state.rawScore.impact_vert,
      }
    },
    isEmpty(state): boolean {
      return state.rawScore === null && !state.loading.score
    },
    weakestSubscore(): SubscoreBucket | null {
      const s = this.score
      if (!s) return null
      let weakest: SubscoreBucket | null = null
      let weakestVal = Infinity
      for (const k of SUBSCORE_KEYS) {
        const v = s.subscores[k]
        if (v !== null && v < weakestVal) {
          weakestVal = v
          weakest = k
        }
      }
      return weakest
    },
  },
  actions: {
    applyRecomputeResult(score: CreditScoreOut) {
      this.rawScore = score
      this.error.score = null
      this.invalidateEligibility()
      this.invalidateHistory()
      this.invalidateRecommendations()
    },
    invalidateScore() {
      this.rawScore = null
    },
    invalidateHistory() {
      this.historyLoadedAt = null
    },
    invalidateEligibility() {
      this.eligibilityLoadedAt = null
    },
    invalidateRecommendations() {
      this.recommendationsLoadedAt = null
    },
    async refreshScore() {
      this.loading.score = true
      this.error.score = null
      try {
        const raw = await creditScoreApi.fetchScore()
        this.rawScore = raw
      }
      catch (e: unknown) {
        // 404 = pas de score = état empty (pas une erreur)
        const status = (e as { status?: number; statusCode?: number })?.status
          ?? (e as { statusCode?: number })?.statusCode
        if (status === 404) {
          this.rawScore = null
        }
        else {
          this.error.score = errMessage(e)
        }
      }
      finally {
        this.loading.score = false
      }
    },
    async refreshHistory(opts: { limit?: number; force?: boolean } = {}) {
      const fresh
        = this.historyLoadedAt !== null
        && Date.now() - this.historyLoadedAt < CACHE_TTL_MS
      if (fresh && !opts.force) return
      this.loading.history = true
      this.error.history = null
      try {
        const dto: ScoreHistoryOutDTO = await creditScoreApi.fetchHistory({
          limit: opts.limit ?? 6,
        })
        this.history = dto.items.map(toHistoryEntry)
        this.historyLoadedAt = Date.now()
      }
      catch (e: unknown) {
        this.error.history = errMessage(e)
      }
      finally {
        this.loading.history = false
      }
    },
    async refreshEligibility(opts: { force?: boolean } = {}) {
      const fresh
        = this.eligibilityLoadedAt !== null
        && Date.now() - this.eligibilityLoadedAt < CACHE_TTL_MS
      if (fresh && !opts.force) return
      this.loading.eligibility = true
      this.error.eligibility = null
      try {
        const dto: EligibilityListDTO = await creditScoreApi.fetchEligibility()
        this.eligibility = dto.items.map((b) => ({
          code: b.code,
          label: b.label,
          description: b.description,
          status: b.status,
          primaryReason: b.primary_reason,
          criteria: b.criteria,
          matchingOfferQuery: b.matching_offer_query,
          sourceId: b.source_id,
        }))
        this.eligibilityLoadedAt = Date.now()
      }
      catch (e: unknown) {
        this.error.eligibility = errMessage(e)
      }
      finally {
        this.loading.eligibility = false
      }
    },
    async refreshRecommendations(opts: { limit?: number; force?: boolean } = {}) {
      const fresh
        = this.recommendationsLoadedAt !== null
        && Date.now() - this.recommendationsLoadedAt < CACHE_TTL_MS
      if (fresh && !opts.force) return
      this.loading.recommendations = true
      this.error.recommendations = null
      try {
        const dto = await creditScoreApi.fetchRecommendations({
          limit: opts.limit ?? 5,
        })
        const subscores = this.score?.subscores ?? emptySubscores()
        const sorted = selectCreditRecommendations(
          dto.items,
          subscores,
          opts.limit ?? 5,
        )
        this.recommendations = sorted.map((r) => ({
          stepId: r.step_id,
          title: r.title,
          description: r.description,
          targetSubscore: r.target_subscore,
          estimatedPointsImpact: r.estimated_credit_points_impact,
        }))
        this.recommendationsLoadedAt = Date.now()
      }
      catch (e: unknown) {
        this.error.recommendations = errMessage(e)
      }
      finally {
        this.loading.recommendations = false
      }
    },
    async refreshAll() {
      await Promise.all([
        this.refreshScore(),
        this.refreshHistory({ force: true }),
      ])
      // Eligibility + recommandations dépendent du score, on les déclenche
      // après pour bénéficier des subscores frais.
      await Promise.all([
        this.refreshEligibility({ force: true }),
        this.refreshRecommendations({ force: true }),
      ])
    },
  },
})
