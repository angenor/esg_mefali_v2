// F47 T024 — Store Pinia useCarbonStore.
//
// Cf. specs/047-empreinte-carbone-ui/data-model.md §3.4.
//
// L'état est cloisonné par tenant (déduit du JWT côté backend) ; côté
// frontend on raisonne en année courante. Cache simple : index multi-année
// avec TTL 60 s, footprint par year sans TTL invalidé sur mutation.

import { defineStore } from "pinia"
import { carbonApi } from "~/services/api/carbon"
import type {
  CarbonEditLineRequest,
  CarbonEditLineResponse,
  CarbonFootprint,
  CarbonIndexEntry,
  CarbonRecomputeResponse,
  WizardDraft,
} from "~/types/carbon"

export const CARBON_INDEX_TTL_MS = 60_000
export const CARBON_WIZARD_TTL_MS = 7 * 24 * 60 * 60 * 1000

interface CarbonStoreState {
  index: CarbonIndexEntry[] | null
  indexLoadedAt: number | null
  footprints: Record<number, CarbonFootprint | null>
  loadingFootprint: Record<number, boolean>
  loadingIndex: boolean
  loadingRecompute: Record<number, boolean>
  loadingEditLine: Record<number, boolean>
  errorByYear: Record<number, string | null>
  selectedYear: number
  wizardDraft: WizardDraft | null
}

function defaultYear(): number {
  return new Date().getUTCFullYear()
}

function wizardKey(accountId: string | null): string {
  return `carbon-wizard-${accountId ?? "anon"}-draft`
}

function readWizardDraft(accountId: string | null): WizardDraft | null {
  if (typeof window === "undefined") return null
  try {
    const raw = window.localStorage.getItem(wizardKey(accountId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as WizardDraft
    if (parsed.saved_at) {
      const age = Date.now() - new Date(parsed.saved_at).getTime()
      if (age > CARBON_WIZARD_TTL_MS) {
        window.localStorage.removeItem(wizardKey(accountId))
        return null
      }
    }
    return parsed
  } catch {
    return null
  }
}

function persistWizardDraft(
  accountId: string | null,
  draft: WizardDraft | null,
): void {
  if (typeof window === "undefined") return
  if (draft === null) {
    window.localStorage.removeItem(wizardKey(accountId))
    return
  }
  window.localStorage.setItem(
    wizardKey(accountId),
    JSON.stringify({ ...draft, saved_at: new Date().toISOString() }),
  )
}

export const useCarbonStore = defineStore("carbon", {
  state: (): CarbonStoreState => ({
    index: null,
    indexLoadedAt: null,
    footprints: {},
    loadingFootprint: {},
    loadingIndex: false,
    loadingRecompute: {},
    loadingEditLine: {},
    errorByYear: {},
    selectedYear: defaultYear(),
    wizardDraft: null,
  }),

  getters: {
    currentFootprint(state): CarbonFootprint | null {
      return state.footprints[state.selectedYear] ?? null
    },
    previousYearFootprint(state): CarbonFootprint | null {
      return state.footprints[state.selectedYear - 1] ?? null
    },
    isEmpty(state): boolean {
      const fp = state.footprints[state.selectedYear]
      return fp === null || fp === undefined
    },
  },

  actions: {
    setSelectedYear(year: number): void {
      this.selectedYear = year
    },

    async loadIndex(opts?: { force?: boolean; limitYears?: number }): Promise<void> {
      const cacheValid =
        !opts?.force &&
        this.indexLoadedAt !== null &&
        Date.now() - this.indexLoadedAt < CARBON_INDEX_TTL_MS
      if (cacheValid) return
      this.loadingIndex = true
      try {
        const entries = await carbonApi.fetchIndex({
          limitYears: opts?.limitYears,
        })
        this.index = entries
        this.indexLoadedAt = Date.now()
      } finally {
        this.loadingIndex = false
      }
    },

    async loadFootprint(year: number): Promise<void> {
      this.loadingFootprint = { ...this.loadingFootprint, [year]: true }
      this.errorByYear = { ...this.errorByYear, [year]: null }
      try {
        const fp = await carbonApi.fetchFootprint(year)
        this.footprints = { ...this.footprints, [year]: fp }
      } catch (err: unknown) {
        const e = err as { status?: number }
        if (e?.status === 404) {
          this.footprints = { ...this.footprints, [year]: null }
        } else {
          this.errorByYear = {
            ...this.errorByYear,
            [year]: err instanceof Error ? err.message : "carbon.errors.generic",
          }
        }
      } finally {
        this.loadingFootprint = { ...this.loadingFootprint, [year]: false }
      }
    },

    applyFootprint(year: number, footprint: CarbonFootprint): void {
      this.footprints = { ...this.footprints, [year]: footprint }
      // Mise à jour de l'index si la year est connue.
      if (this.index) {
        const idx = this.index.findIndex((e) => e.year === year)
        const entry: CarbonIndexEntry = {
          footprint_id: footprint.id,
          year,
          total_tco2e: footprint.total_tco2e,
          computed_at: footprint.computed_at ?? new Date().toISOString(),
          version: footprint.version ?? 1,
        }
        if (idx >= 0) {
          const next = [...this.index]
          next[idx] = entry
          this.index = next
        } else {
          this.index = [entry, ...this.index].sort((a, b) => b.year - a.year)
        }
      }
    },

    async recompute(year: number): Promise<CarbonRecomputeResponse | null> {
      if (this.loadingRecompute[year]) return null
      this.loadingRecompute = { ...this.loadingRecompute, [year]: true }
      try {
        const response = await carbonApi.recompute(year)
        this.applyFootprint(year, response)
        return response
      } finally {
        this.loadingRecompute = { ...this.loadingRecompute, [year]: false }
      }
    },

    async editLine(
      year: number,
      payload: CarbonEditLineRequest,
    ): Promise<CarbonEditLineResponse | null> {
      if (this.loadingEditLine[year]) return null
      this.loadingEditLine = { ...this.loadingEditLine, [year]: true }
      try {
        const response = await carbonApi.editLine(year, payload)
        this.applyFootprint(year, response)
        return response
      } finally {
        this.loadingEditLine = { ...this.loadingEditLine, [year]: false }
      }
    },

    invalidateYear(year: number): void {
      const next = { ...this.footprints }
      delete next[year]
      this.footprints = next
    },

    invalidateIndex(): void {
      this.indexLoadedAt = null
    },

    hydrateWizardDraft(accountId: string | null): void {
      this.wizardDraft = readWizardDraft(accountId)
    },

    setWizardDraft(accountId: string | null, draft: WizardDraft | null): void {
      this.wizardDraft = draft
      persistWizardDraft(accountId, draft)
    },
  },
})
