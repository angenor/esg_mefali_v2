// F46 T016 — Store Pinia useScoringStore.
//
// Cf. specs/046-scoring-esg-ui/data-model.md §3.

import { defineStore } from "pinia"
import { scoringApi, type EntityType } from "~/services/api/scoring"
import { useChatEventBus } from "~/composables/useChatEventBus"
import type { EventBusEvent } from "~/types/chat"
import {
  SCORING_EDITABLE_INDICATEUR_CODES,
  SCORING_INDICATEUR_TO_ENTREPRISE_PATH,
} from "~/lib/scoringEditableIndicateurs"
import {
  mapIndicateursByPillar,
  type SourceMap,
} from "~/lib/mapIndicateursByPillar"
import type {
  CoveredIndicatorOut,
  CoveredIndicatorVM,
  MissingIndicatorOut,
  MissingIndicatorVM,
  PillarBucketVM,
  PillarCode,
  ScoreDetailOut,
  ScoreDetailVM,
  ScoreHistoryEntry,
  ScoreHistoryEntryVM,
  ScoreSummaryOut,
  ScoreSummaryVM,
  ScoringSnapshotVM,
} from "~/types/scoring"

export const SCORING_CACHE_TTL_MS = 60_000
export const SCORING_ECHO_GUARD_MS = 500

function summaryFromOut(o: ScoreSummaryOut): ScoreSummaryVM {
  return {
    referentielCode: o.referentiel_code,
    referentielId: o.referentiel_id,
    referentielVersion: o.referentiel_version,
    scoreGlobal: o.score_global,
    scoresByPillar: o.scores_by_pillar ?? {},
    coverageRatio: o.coverage_ratio,
    computedAt: o.computed_at,
  }
}

function coveredFromOut(c: CoveredIndicatorOut): CoveredIndicatorVM {
  return {
    indicateurId: c.indicateur_id,
    indicateurCode: c.indicateur_code,
    pillar: c.pillar,
    value: c.value,
    normalizedValue: c.normalized_value,
    weight: c.weight,
    contribution: c.contribution,
    sourceId: c.source_id,
  }
}

function missingFromOut(m: MissingIndicatorOut): MissingIndicatorVM {
  return {
    indicateurId: m.indicateur_id,
    indicateurCode: m.indicateur_code,
    pillar: m.pillar,
    reason: m.reason,
  }
}

function detailFromOut(d: ScoreDetailOut): ScoreDetailVM {
  return {
    ...summaryFromOut(d),
    indicateursCouverts: (d.indicateurs_couverts ?? []).map(coveredFromOut),
    indicateursManquants: (d.indicateurs_manquants ?? []).map(missingFromOut),
    sourcesUsed: d.sources_used ?? [],
  }
}

function historyEntryFromOut(e: ScoreHistoryEntry): ScoreHistoryEntryVM {
  return {
    scoreCalculationId: e.score_calculation_id,
    computedAt: e.computed_at,
    scoreGlobal: e.score_global,
    referentielVersion: e.referentiel_version,
  }
}

interface CacheEntry<T> {
  value: T
  fetchedAt: number
}

interface ScoringState {
  entityType: EntityType
  entityId: string | null

  currentReferentielCode: string | null

  summariesByRef: Record<string, ScoreSummaryVM>
  detailsByRef: Record<string, ScoreDetailVM>
  detailsCacheByRef: Record<string, CacheEntry<true>>
  historyByRef: Record<string, ScoreHistoryEntryVM[]>
  historyCacheByRef: Record<string, CacheEntry<true>>

  loadingByRef: Record<string, "idle" | "loading" | "success" | "error">
  errorByRef: Record<string, string | null>

  recomputingByRef: Record<string, boolean>

  editingIndicateurIds: string[]

  snapshot: ScoringSnapshotVM

  // sources cache (populated by component layers via useSourceFetch — exposé pour mapping)
  sources: Record<string, { status: "verified" | "revoked" | string }>

  // anti-loop guard pour les events bus locaux
  recentLocalEmissions: Record<string, number>
}

export interface EditIndicateurInput {
  indicateurId: string
  indicateurCode: string
  newValue: unknown
  refCode: string
}

export interface OnChatEntityUpdatedPayload {
  entityType: "indicateur" | "score_calculation" | "entreprise" | "projet"
  entityId?: string
  source?: "manual" | "tool" | "llm" | "import" | "admin"
  meta?: {
    referentiel_code?: string
    field?: string
    indicateur_code?: string
  }
}

export const useScoringStore = defineStore("scoring", {
  state: (): ScoringState => ({
    entityType: "entreprise",
    entityId: null,
    currentReferentielCode: null,
    summariesByRef: {},
    detailsByRef: {},
    detailsCacheByRef: {},
    historyByRef: {},
    historyCacheByRef: {},
    loadingByRef: {},
    errorByRef: {},
    recomputingByRef: {},
    editingIndicateurIds: [],
    snapshot: {
      active: false,
      frozenCalculationId: null,
      frozenSummary: null,
      frozenAt: null,
    },
    sources: {},
    recentLocalEmissions: {},
  }),
  getters: {
    currentSummary(state): ScoreSummaryVM | null {
      const code = state.currentReferentielCode
      if (!code) return null
      if (state.snapshot.active && state.snapshot.frozenSummary) {
        return state.snapshot.frozenSummary
      }
      return state.summariesByRef[code] ?? null
    },
    currentDetail(state): ScoreDetailVM | null {
      const code = state.currentReferentielCode
      if (!code) return null
      return state.detailsByRef[code] ?? null
    },
    currentHistory(state): ScoreHistoryEntryVM[] {
      const code = state.currentReferentielCode
      if (!code) return []
      return state.historyByRef[code] ?? []
    },
    isLoading(state): boolean {
      const code = state.currentReferentielCode
      if (!code) return false
      return state.loadingByRef[code] === "loading"
    },
    isRecomputing(state): boolean {
      const code = state.currentReferentielCode
      if (!code) return false
      return state.recomputingByRef[code] === true
    },
    isSnapshot(state): boolean {
      return state.snapshot.active
    },
    availableReferentiels(state): string[] {
      return Object.keys(state.summariesByRef)
    },
    pillarsBuckets(): PillarBucketVM[] {
      const detail = this.currentDetail as ScoreDetailVM | null
      if (!detail) return []
      const sourcesMap: SourceMap = new Map(Object.entries(this.sources))
      return mapIndicateursByPillar(
        detail,
        sourcesMap,
        SCORING_EDITABLE_INDICATEUR_CODES,
      )
    },
    coveragePercent(): number {
      const summary = this.currentSummary as ScoreSummaryVM | null
      if (!summary?.coverageRatio) return 0
      return Math.round(summary.coverageRatio * 100)
    },
  },
  actions: {
    setEntity(type: EntityType, id: string): void {
      this.entityType = type
      this.entityId = id
    },

    async loadSummaries(): Promise<void> {
      if (!this.entityId) return
      try {
        const data = await scoringApi.listSummaries(
          this.entityType,
          this.entityId,
        )
        const map: Record<string, ScoreSummaryVM> = {}
        for (const s of data.scores ?? []) {
          map[s.referentiel_code] = summaryFromOut(s)
        }
        this.summariesByRef = map
      } catch (err: unknown) {
        const code = this.currentReferentielCode ?? "_global"
        this.errorByRef[code] = err instanceof Error ? err.message : "load_failed"
        throw err
      }
    },

    async loadDetail(refCode: string, force = false): Promise<void> {
      if (!this.entityId) return
      const now = Date.now()
      const cached = this.detailsCacheByRef[refCode]
      if (
        !force &&
        cached &&
        now - cached.fetchedAt < SCORING_CACHE_TTL_MS &&
        this.detailsByRef[refCode]
      ) {
        return
      }
      this.loadingByRef[refCode] = "loading"
      this.errorByRef[refCode] = null
      try {
        const data = await scoringApi.getDetail(
          this.entityType,
          this.entityId,
          refCode,
        )
        this.detailsByRef[refCode] = detailFromOut(data)
        // un détail à jour rafraichit le summary aussi.
        this.summariesByRef[refCode] = summaryFromOut(data)
        this.detailsCacheByRef[refCode] = { value: true, fetchedAt: Date.now() }
        this.loadingByRef[refCode] = "success"
      } catch (err: unknown) {
        this.loadingByRef[refCode] = "error"
        this.errorByRef[refCode] =
          err instanceof Error ? err.message : "load_failed"
        throw err
      }
    },

    async loadHistory(refCode: string, limit = 12, force = false): Promise<void> {
      if (!this.entityId) return
      const now = Date.now()
      const cached = this.historyCacheByRef[refCode]
      if (
        !force &&
        cached &&
        now - cached.fetchedAt < SCORING_CACHE_TTL_MS &&
        this.historyByRef[refCode]
      ) {
        return
      }
      try {
        const data = await scoringApi.getHistory(
          this.entityType,
          this.entityId,
          refCode,
          limit,
        )
        this.historyByRef[refCode] = (data.entries ?? []).map(historyEntryFromOut)
        this.historyCacheByRef[refCode] = { value: true, fetchedAt: Date.now() }
      } catch (err: unknown) {
        this.errorByRef[refCode] =
          err instanceof Error ? err.message : "history_failed"
        // ne pas relancer — toast non bloquant côté composant.
      }
    },

    async setCurrentReferentiel(code: string): Promise<void> {
      this.currentReferentielCode = code
      const promises: Promise<void>[] = []
      if (!this.detailsByRef[code]) promises.push(this.loadDetail(code))
      if (!this.historyByRef[code]) promises.push(this.loadHistory(code))
      await Promise.all(promises).catch(() => {
        /* errors already stored */
      })
    },

    async recompute(refCode: string, opts: { emitBus?: boolean } = {}): Promise<void> {
      const { emitBus = true } = opts
      if (this.snapshot.active) {
        throw new Error("snapshot_active")
      }
      if (this.recomputingByRef[refCode]) {
        throw new Error("already_recomputing")
      }
      if (!this.entityId) return
      this.recomputingByRef[refCode] = true
      try {
        const data = await scoringApi.recompute(
          this.entityType,
          this.entityId,
          refCode,
        )
        this.detailsByRef[refCode] = detailFromOut(data)
        this.summariesByRef[refCode] = summaryFromOut(data)
        this.detailsCacheByRef[refCode] = { value: true, fetchedAt: Date.now() }
        // invalide history → re-fetch.
        delete this.historyCacheByRef[refCode]
        await this.loadHistory(refCode, 12, true)
        if (emitBus) {
          this.emitLocalScoreCalculation(refCode)
        }
      } catch (err: unknown) {
        this.errorByRef[refCode] =
          err instanceof Error ? err.message : "recompute_failed"
        throw err
      } finally {
        this.recomputingByRef[refCode] = false
      }
    },

    async editIndicateur(
      input: EditIndicateurInput,
      currentEntreprise: Record<string, unknown> | null = null,
    ): Promise<void> {
      if (this.snapshot.active) {
        throw new Error("snapshot_active")
      }
      const path = SCORING_INDICATEUR_TO_ENTREPRISE_PATH[input.indicateurCode]
      if (!path) {
        throw new Error("not_editable_here")
      }
      this.editingIndicateurIds.push(input.indicateurId)
      try {
        await scoringApi.editIndicateurValue(
          input.indicateurCode,
          input.newValue,
          currentEntreprise,
        )
        // Recalcul (on suppress emit interne pour contrôler l'ordre).
        await this.recompute(input.refCode, { emitBus: false })
        // Émission events dans l'ordre : indicateur → score_calculation.
        this.emitLocalIndicateur(
          input.indicateurId,
          input.indicateurCode,
          input.refCode,
        )
        this.emitLocalScoreCalculation(input.refCode)
      } finally {
        this.editingIndicateurIds = this.editingIndicateurIds.filter(
          (id) => id !== input.indicateurId,
        )
      }
    },

    emitLocalIndicateur(
      indicateurId: string,
      indicateurCode: string,
      refCode: string,
    ): void {
      this.trackLocalEmission("indicateur", indicateurId)
      try {
        const evt: EventBusEvent = {
          eventType: "entity_updated",
          entityType: "indicateur",
          entityId: indicateurId,
          fieldsUpdated: [indicateurCode],
          source: "manual",
          ts: new Date().toISOString(),
        }
        useChatEventBus().emit("entity_updated", evt)
      } catch {
        /* bus unavailable in test contexts is fine */
      }
      void refCode
    },

    emitLocalScoreCalculation(refCode: string): void {
      const calcId =
        this.detailsByRef[refCode]?.referentielId ?? `calc-${refCode}`
      this.trackLocalEmission("score_calculation", calcId)
      try {
        const evt: EventBusEvent = {
          eventType: "entity_updated",
          entityType: "score_calculation",
          entityId: calcId,
          fieldsUpdated: [refCode],
          source: "manual",
          ts: new Date().toISOString(),
        }
        useChatEventBus().emit("entity_updated", evt)
      } catch {
        /* idem */
      }
    },

    async enterSnapshot(calcId: string): Promise<void> {
      const code = this.currentReferentielCode
      if (!code) return
      const entry = (this.historyByRef[code] ?? []).find(
        (e) => e.scoreCalculationId === calcId,
      )
      if (!entry) return
      const baseSummary = this.summariesByRef[code] ?? null
      const frozenSummary: ScoreSummaryVM | null = baseSummary
        ? {
            ...baseSummary,
            scoreGlobal: entry.scoreGlobal,
            referentielVersion: entry.referentielVersion,
            computedAt: entry.computedAt,
          }
        : null
      this.snapshot = {
        active: true,
        frozenCalculationId: calcId,
        frozenSummary,
        frozenAt: entry.computedAt,
      }
      this.editingIndicateurIds = []
    },

    exitSnapshot(): void {
      this.snapshot = {
        active: false,
        frozenCalculationId: null,
        frozenSummary: null,
        frozenAt: null,
      }
    },

    onChatEntityUpdated(payload: OnChatEntityUpdatedPayload): void {
      const code = this.currentReferentielCode
      if (!code) return
      // Anti-loop : event 'manual' issu d'une émission locale récente est ignoré.
      const key = `${payload.entityType}:${payload.entityId ?? ""}`
      const ts = this.recentLocalEmissions[key]
      if (
        payload.source === "manual" &&
        ts &&
        Date.now() - ts < SCORING_ECHO_GUARD_MS
      ) {
        return
      }

      if (payload.entityType === "indicateur") {
        const ic = payload.meta?.indicateur_code
        // Si meta.indicateur_code connu mais aucun ref chargé ne le contient → no-op.
        if (ic) {
          const refsContaining = Object.entries(this.detailsByRef).filter(
            ([, d]) =>
              d.indicateursCouverts.some((c) => c.indicateurCode === ic) ||
              d.indicateursManquants.some((m) => m.indicateurCode === ic),
          )
          if (refsContaining.length === 0) return
        }
        delete this.detailsCacheByRef[code]
        delete this.historyCacheByRef[code]
      } else if (payload.entityType === "score_calculation") {
        delete this.detailsCacheByRef[code]
        delete this.historyCacheByRef[code]
      } else if (payload.entityType === "entreprise") {
        const field = payload.meta?.field
        const fields = new Set(
          Object.values(SCORING_INDICATEUR_TO_ENTREPRISE_PATH).map((p) => p.field),
        )
        if (!field || !fields.has(field)) return
        delete this.detailsCacheByRef[code]
        delete this.historyCacheByRef[code]
      } else {
        return
      }
    },

    trackLocalEmission(entityType: string, entityId: string): void {
      const key = `${entityType}:${entityId}`
      this.recentLocalEmissions[key] = Date.now()
    },

    setSourceStatus(sourceId: string, status: "verified" | "revoked" | string): void {
      this.sources[sourceId] = { status }
    },
  },
})
