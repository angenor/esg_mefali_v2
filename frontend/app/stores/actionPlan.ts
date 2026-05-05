// F45 T013 — Store Pinia du plan d'action ESG.
//
// Cf. specs/045-plan-action-ui/data-model.md § 3.
import { defineStore } from "pinia"
import type {
  ActionPlan,
  ActionStep,
  ActionStepPatchPayload,
  CompletionStats,
  Horizon,
  PlanFilters,
  ResponsibleOption,
} from "~/types/actionPlan"

export const PLAN_CACHE_TTL_MS = 60_000
export const ECHO_GUARD_MS = 500

interface RuntimeConfigShape {
  public?: { apiBase?: string }
}

function apiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = (globalThis as any).useRuntimeConfig?.() as RuntimeConfigShape | undefined
  return String(cfg?.public?.apiBase ?? "").replace(/\/$/, "")
}

type FetchFn = <T>(u: string, o?: Record<string, unknown>) => Promise<T>
function fetcher(): FetchFn {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const f = (globalThis as any).$fetch as FetchFn | undefined
  if (!f) throw new Error("$fetch unavailable")
  return f
}

export interface StepUiState {
  loading: boolean
  error: string | null
  optimisticOverlay: Partial<ActionStep> | null
}

interface ActionPlanState {
  plan: ActionPlan | null
  loading: boolean
  error: string | null
  lastFetchedAt: number | null
  filters: PlanFilters
  horizonView: Horizon
  stepStates: Record<string, StepUiState>
  pendingMutations: Record<string, ActionStepPatchPayload[]>
  regenerating: boolean
  recentLocalEmits: Record<string, number>
  _inflightFetch: Promise<void> | null
}

const HORIZON_FILTER_THRESHOLDS: Record<Horizon, number> = { 6: 6, 12: 12, 24: 24 }

function deltaMonths(from: string, to: string | null | undefined): number | null {
  if (!to) return null
  const f = new Date(from)
  const t = new Date(to)
  if (Number.isNaN(f.getTime()) || Number.isNaN(t.getTime())) return null
  return Math.round((t.getTime() - f.getTime()) / (30 * 24 * 60 * 60 * 1000))
}

export const useActionPlanStore = defineStore("actionPlan", {
  state: (): ActionPlanState => ({
    plan: null,
    loading: false,
    error: null,
    lastFetchedAt: null,
    filters: { priority: [], status: [], horizon: null, responsibleUserId: null },
    horizonView: 24,
    stepStates: {},
    pendingMutations: {},
    regenerating: false,
    recentLocalEmits: {},
    _inflightFetch: null,
  }),
  getters: {
    currentPlan(state): ActionPlan | null {
      return state.plan
    },
    currentVersion(state): number | null {
      return state.plan?.version ?? null
    },
    visibleSteps(state): ActionStep[] {
      if (!state.plan) return []
      const { generated_at, steps } = state.plan
      const horizonCap = HORIZON_FILTER_THRESHOLDS[state.horizonView]
      return steps
        .map((s) => {
          const overlay = state.stepStates[s.id]?.optimisticOverlay
          return overlay ? { ...s, ...overlay } : s
        })
        .filter((s) => {
          const months = deltaMonths(generated_at, s.horizon_at)
          // unscheduled passe toujours
          if (months !== null && months > horizonCap) return false
          if (state.filters.priority.length && !state.filters.priority.includes(s.priority))
            return false
          if (state.filters.status.length && !state.filters.status.includes(s.status))
            return false
          if (
            state.filters.responsibleUserId &&
            s.responsible_user_id !== state.filters.responsibleUserId
          )
            return false
          return true
        })
    },
    completionStats(state): CompletionStats {
      if (!state.plan) {
        return { totalVisible: 0, doneVisible: 0, percent: 0, hasData: false }
      }
      const horizonCap = HORIZON_FILTER_THRESHOLDS[state.horizonView]
      const { generated_at, steps } = state.plan
      const visible = steps
        .map((s) => {
          const overlay = state.stepStates[s.id]?.optimisticOverlay
          return overlay ? { ...s, ...overlay } : s
        })
        .filter((s) => {
          const months = deltaMonths(generated_at, s.horizon_at)
          return months === null || months <= horizonCap
        })
      const total = visible.length
      const done = visible.filter((s) => s.status === "done").length
      return {
        totalVisible: total,
        doneVisible: done,
        percent: total === 0 ? 0 : Math.round((done / total) * 100),
        hasData: total > 0,
      }
    },
    responsibleOptions(state): ResponsibleOption[] {
      if (!state.plan) return []
      const ids = new Set<string>()
      for (const s of state.plan.steps) {
        if (s.responsible_user_id) ids.add(s.responsible_user_id)
      }
      return Array.from(ids).map((id) => ({ id, label: id.slice(0, 8) }))
    },
  },
  actions: {
    async fetchPlan(force = false): Promise<void> {
      const now = Date.now()
      if (
        !force &&
        this.lastFetchedAt !== null &&
        now - this.lastFetchedAt < PLAN_CACHE_TTL_MS &&
        this.plan
      ) {
        return
      }
      if (this._inflightFetch) {
        return this._inflightFetch
      }
      const url = `${apiBase()}/me/action-plan`
      this.loading = true
      this.error = null
      const promise = (async (): Promise<void> => {
        try {
          const data = await fetcher()<ActionPlan>(url, { credentials: "include" })
          this.plan = data
          this.lastFetchedAt = Date.now()
        } catch (err: unknown) {
          this.error = err instanceof Error ? err.message : "load_failed"
          throw err
        } finally {
          this.loading = false
          this._inflightFetch = null
        }
      })()
      this._inflightFetch = promise
      return promise
    },
    setFilters(next: Partial<PlanFilters>): void {
      this.filters = { ...this.filters, ...next }
    },
    resetFilters(): void {
      this.filters = { priority: [], status: [], horizon: null, responsibleUserId: null }
    },
    setHorizonView(h: Horizon): void {
      this.horizonView = h
    },
    _ensureStepState(stepId: string): StepUiState {
      if (!this.stepStates[stepId]) {
        this.stepStates[stepId] = { loading: false, error: null, optimisticOverlay: null }
      }
      return this.stepStates[stepId]!
    },
    trackLocalEmit(stepId: string): void {
      this.recentLocalEmits[stepId] = Date.now()
    },
    isEcho(stepId: string): boolean {
      const ts = this.recentLocalEmits[stepId]
      if (!ts) return false
      return Date.now() - ts < ECHO_GUARD_MS
    },
    async applyOptimisticPatch(stepId: string, patch: ActionStepPatchPayload): Promise<void> {
      if (!this.plan) throw new Error("no_plan")
      // File FIFO par step_id : on enchaîne les mutations.
      const queue = (this.pendingMutations[stepId] ??= [])
      queue.push(patch)
      if (queue.length > 1) {
        // Une mutation est déjà en vol pour ce step ; on attend son tour.
        return new Promise((resolve, reject) => {
          const tick = (): void => {
            if (this.pendingMutations[stepId]?.[0] === patch) {
              this._runPatch(stepId, patch).then(resolve, reject)
            } else if (this.pendingMutations[stepId]?.includes(patch)) {
              setTimeout(tick, 16)
            } else {
              // mutation rejetée par un rollback en amont
              reject(new Error("aborted_by_previous_failure"))
            }
          }
          setTimeout(tick, 16)
        })
      }
      return this._runPatch(stepId, patch)
    },
    async _runPatch(stepId: string, patch: ActionStepPatchPayload): Promise<void> {
      const ui = this._ensureStepState(stepId)
      const previous = ui.optimisticOverlay
      ui.optimisticOverlay = { ...(previous ?? {}), ...patch }
      ui.loading = true
      ui.error = null
      const url = `${apiBase()}/me/action-plan/steps/${stepId}`
      try {
        const updated = await fetcher()<ActionStep>(url, {
          method: "PATCH",
          body: patch,
          credentials: "include",
        })
        // Remplace le step concerné dans plan.steps en gardant la référence
        // pour les autres steps (re-render minimal).
        if (this.plan) {
          this.plan = {
            ...this.plan,
            steps: this.plan.steps.map((s) => (s.id === stepId ? { ...s, ...updated } : s)),
          }
        }
        ui.optimisticOverlay = null
        ui.error = null
      } catch (err: unknown) {
        ui.optimisticOverlay = previous
        ui.error = err instanceof Error ? err.message : "patch_failed"
        // Vider la file pour ce step → toutes les mutations en attente sont
        // annulées (sécurité : éviter d'envoyer une suite optimiste sur état
        // potentiellement incohérent).
        this.pendingMutations[stepId] = []
        ui.loading = false
        throw err
      } finally {
        const queue = this.pendingMutations[stepId]
        if (queue && queue[0] === patch) queue.shift()
        if (!this.pendingMutations[stepId]?.length) {
          delete this.pendingMutations[stepId]
        }
        ui.loading = (this.pendingMutations[stepId]?.length ?? 0) > 0
      }
    },
    async invalidateStep(stepId: string): Promise<void> {
      if (!this.plan) return
      // Re-fetch ciblé : pas d'endpoint dédié → fetch plein puis remplacement
      // ciblé du seul step concerné (les autres références sont conservées).
      const url = `${apiBase()}/me/action-plan`
      try {
        const fresh = await fetcher()<ActionPlan>(url, { credentials: "include" })
        const updated = fresh.steps.find((s) => s.id === stepId)
        if (!updated || !this.plan) return
        const ui = this._ensureStepState(stepId)
        ui.optimisticOverlay = null
        ui.error = null
        this.plan = {
          ...this.plan,
          steps: this.plan.steps.map((s) => (s.id === stepId ? updated : s)),
        }
        this.lastFetchedAt = Date.now()
      } catch (err: unknown) {
        this.error = err instanceof Error ? err.message : "invalidate_failed"
      }
    },
    async regenerate(horizon: Horizon): Promise<void> {
      if (this.regenerating) return
      this.regenerating = true
      this.error = null
      try {
        const url = `${apiBase()}/me/action-plan/generate?horizon=${horizon}`
        const fresh = await fetcher()<ActionPlan>(url, {
          method: "POST",
          credentials: "include",
        })
        this.plan = fresh
        this.stepStates = {}
        this.pendingMutations = {}
        this.lastFetchedAt = Date.now()
      } catch (err: unknown) {
        this.error = err instanceof Error ? err.message : "regenerate_failed"
        throw err
      } finally {
        this.regenerating = false
      }
    },
  },
})
