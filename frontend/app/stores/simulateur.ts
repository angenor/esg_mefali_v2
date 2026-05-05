// F51 T015 — Store Pinia useSimulateurStore.

import { defineStore } from "pinia"
import { simulateurApi } from "~/services/api/simulateur"
import { emitCandidatureEvent } from "~/lib/candidatureEvents"
import type {
  SimulateurInputs,
  SimulationResults,
  SimulationSavedRow,
} from "~/types/simulateur"

const DEFAULT_INPUTS: SimulateurInputs = {
  montant: { amount: "100000", currency: "EUR" },
  duree_mois: 60,
  type_investissement: "renouvelable_solaire",
  part_subvention_pct: 0,
}

interface State {
  inputs: SimulateurInputs
  results: SimulationResults | null
  computing: boolean
  error: string | null
  history: SimulationSavedRow[]
  historyLoading: boolean
  saveSheetOpen: boolean
  abort: AbortController | null
}

export const useSimulateurStore = defineStore("simulateur", {
  state: (): State => ({
    inputs: { ...DEFAULT_INPUTS },
    results: null,
    computing: false,
    error: null,
    history: [],
    historyLoading: false,
    saveSheetOpen: false,
    abort: null,
  }),

  actions: {
    setInput<K extends keyof SimulateurInputs>(
      key: K,
      value: SimulateurInputs[K],
    ): void {
      this.inputs = { ...this.inputs, [key]: value }
    },

    async compute(): Promise<void> {
      // Annule tout calcul en vol.
      if (this.abort) this.abort.abort()
      const ctrl = new AbortController()
      this.abort = ctrl
      this.computing = true
      this.error = null
      try {
        const out = await simulateurApi.compute(
          {
            projet_id: null,
            offre_id: null,
            hypotheses: this.inputs,
          },
          ctrl.signal,
        )
        // Si une autre requête a remplacé l'AbortController, on jette le résultat.
        if (this.abort === ctrl) {
          this.results = out
        }
      } catch (err) {
        const e = err as Error & { name?: string }
        if (e.name === "AbortError") return
        this.error = e.message ?? "compute_failed"
      } finally {
        if (this.abort === ctrl) {
          this.computing = false
          this.abort = null
        }
      }
    },

    async save(label: string): Promise<boolean> {
      if (!this.results) return false
      try {
        const r = await simulateurApi.save({
          label,
          projet_id: null,
          offre_id: null,
          hypotheses: this.inputs,
          results: this.results,
        })
        emitCandidatureEvent("simulateur:saved", {
          simulation_id: r.id,
          label: r.label,
        })
        await this.fetchHistory()
        return true
      } catch (err) {
        this.error = (err as Error).message ?? "save_failed"
        return false
      }
    },

    async fetchHistory(): Promise<void> {
      this.historyLoading = true
      try {
        const out = await simulateurApi.listHistory(50)
        this.history = out.items
      } catch (err) {
        this.error = (err as Error).message ?? "history_failed"
      } finally {
        this.historyLoading = false
      }
    },

    async softDelete(id: string): Promise<void> {
      try {
        await simulateurApi.softDelete(id)
        this.history = this.history.filter((h) => h.id !== id)
      } catch (err) {
        this.error = (err as Error).message ?? "delete_failed"
      }
    },

    rehydrateFromQuery(query: Record<string, string | string[]>): void {
      const montant = first(query.montant)
      const duree = first(query.duree)
      if (montant) {
        this.inputs.montant = {
          amount: montant,
          currency: (first(query.currency) as "EUR" | "XOF") ?? "EUR",
        }
      }
      if (duree) {
        const n = Number.parseInt(duree, 10)
        if (!Number.isNaN(n)) this.inputs.duree_mois = n
      }
    },

    reset(): void {
      this.inputs = { ...DEFAULT_INPUTS }
      this.results = null
      this.error = null
    },
  },
})

function first(v: string | string[] | undefined): string | undefined {
  if (Array.isArray(v)) return v[0]
  return v
}
