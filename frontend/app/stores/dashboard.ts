// F44 T008 — Store Pinia dashboard PME (cache 60 s + invalidations ciblées par bloc).
//
// Cf. specs/044-dashboard-pme-ui/data-model.md et contracts/frontend-components.md C-CMP-3.
import { defineStore } from "pinia"
import type { BlockKey } from "~/lib/dashboardEventMap"

export interface ScoreEntry {
  referentiel_code: string
  referentiel_version: number
  score_global: string // Decimal P5
  coverage_ratio?: string | null
  computed_at: string
  by_axis?: { e: number; s: number; g: number } | null
  source_count?: number | null
}

export interface CarbonEntry {
  year: number
  total_tco2e: string // Decimal P5
  computed_at: string
  trend?: { quarter: string; tco2e: string }[] | null
}

export interface CreditScoreOut {
  solvabilite: number
  impact_vert: number
  combine: number
  methodologie_version: number
  coherence_warning: boolean
  computed_at: string
  eligibility_badges?: string[] | null
}

export interface CandidatureRecent {
  id: string
  projet_id: string
  offre_id: string
  statut: string
  soumission_at: string | null
  created_at: string
  projet_label?: string | null
  offre_label?: string | null
}

export interface CandidaturesBlock {
  counters_by_statut: Record<string, number>
  total: number
  recent: CandidatureRecent[]
}

export interface RapportRecent {
  id: string
  entity_type: string
  entity_id: string
  referentiels: string[]
  language: string
  generated_at: string
  title?: string | null
  download_href?: string | null
}

export interface RapportsBlock {
  total: number
  recent: RapportRecent[]
}

export interface AttestationRecent {
  id: string
  public_id: string
  generated_at: string
  valid_until: string
  revoked_at: string | null
}

export interface AttestationsBlock {
  active: number
  revoked: number
  recent: AttestationRecent[]
}

export interface ActionStepEntry {
  id: string
  title: string
  category: string
  priority: "haute" | "moyenne" | "basse"
  status: "pending" | "done" | "skipped"
  horizon_at: string
}

export interface DashboardSummaryOut {
  account_id: string
  scores: ScoreEntry[]
  carbon: CarbonEntry[]
  credit_score: CreditScoreOut | null
  candidatures: CandidaturesBlock
  rapports: RapportsBlock
  attestations: AttestationsBlock
  next_actions: ActionStepEntry[]
  generated_at: string
}

interface DashboardState {
  summary: DashboardSummaryOut | null
  generatedAt: string | null
  blockErrors: Partial<Record<BlockKey | "*", string>>
  loading: boolean
  invalidatedBlocks: Set<BlockKey>
  /** Lock concurrentiel : promesse en cours pour serialiser les fetch parallèles. */
  inflight: Promise<void> | null
}

export interface FetchSummaryOptions {
  scope?: BlockKey[]
}

const SCOPE_TO_KEYS: Readonly<Record<BlockKey, ReadonlyArray<keyof DashboardSummaryOut>>> = {
  scores: ["scores"],
  carbon: ["carbon"],
  credit_score: ["credit_score"],
  candidatures: ["candidatures"],
  rapports: ["rapports"],
  attestations: ["attestations"],
  next_actions: ["next_actions"],
}

export const useDashboardStore = defineStore("dashboard", {
  state: (): DashboardState => ({
    summary: null,
    generatedAt: null,
    blockErrors: {},
    loading: false,
    invalidatedBlocks: new Set<BlockKey>(),
    inflight: null,
  }),

  actions: {
    async fetchSummary(opts: FetchSummaryOptions = {}): Promise<void> {
      // Lock concurrentiel : sérialise les appels parallèles.
      if (this.inflight) {
        await this.inflight
        return
      }
      this.loading = true
      const apiBase = (globalThis.useRuntimeConfig?.() as { public?: { apiBase?: string } })
        ?.public?.apiBase ?? ""
      const url = `${apiBase}/me/dashboard/summary`
      const fetchFn = globalThis.$fetch as
        | (<T>(u: string, o?: Record<string, unknown>) => Promise<T>)
        | undefined
      const promise = (async () => {
        try {
          if (!fetchFn) throw new Error("$fetch unavailable")
          const data = await fetchFn<DashboardSummaryOut>(url, { credentials: "include" })
          this.applySummary(data, opts.scope)
          // Effacer les erreurs des blocs réussis.
          if (opts.scope && opts.scope.length > 0) {
            const next = { ...this.blockErrors }
            for (const k of opts.scope) delete next[k]
            this.blockErrors = next
          } else {
            this.blockErrors = {}
          }
          // Consommer les invalidations couvertes par ce fetch.
          if (!opts.scope) {
            this.invalidatedBlocks = new Set<BlockKey>()
          } else {
            const remaining = new Set(this.invalidatedBlocks)
            for (const k of opts.scope) remaining.delete(k)
            this.invalidatedBlocks = remaining
          }
        } catch (err) {
          const message = err instanceof Error ? err.message : "Erreur inconnue"
          if (opts.scope && opts.scope.length > 0) {
            const next = { ...this.blockErrors }
            for (const k of opts.scope) next[k] = message
            this.blockErrors = next
          } else {
            this.blockErrors = { ...this.blockErrors, "*": message }
          }
        } finally {
          this.loading = false
        }
      })()
      this.inflight = promise
      try {
        await promise
      } finally {
        this.inflight = null
      }
    },

    /** Applique le résultat backend au state. Si `scope` est fourni, n'écrit que ces clés. */
    applySummary(data: DashboardSummaryOut, scope?: BlockKey[]): void {
      if (!scope || scope.length === 0 || !this.summary) {
        this.summary = data
      } else {
        const merged: DashboardSummaryOut = { ...this.summary }
        for (const block of scope) {
          for (const key of SCOPE_TO_KEYS[block]) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ;(merged as any)[key] = (data as any)[key]
          }
        }
        // Toujours actualiser le timestamp global.
        merged.generated_at = data.generated_at
        this.summary = merged
      }
      this.generatedAt = data.generated_at
    },

    invalidate(block: BlockKey): void {
      const next = new Set(this.invalidatedBlocks)
      next.add(block)
      this.invalidatedBlocks = next
    },

    reset(): void {
      this.summary = null
      this.generatedAt = null
      this.blockErrors = {}
      this.loading = false
      this.invalidatedBlocks = new Set<BlockKey>()
      this.inflight = null
    },
  },
})
