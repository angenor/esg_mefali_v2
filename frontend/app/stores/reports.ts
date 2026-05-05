// F49 T015 — Store Pinia useReportsStore.
//
// État + actions pour `pages/rapports/index.vue` et `GenerateReportModal.vue`.
// Cf. specs/049-rapports-attestations-ui/data-model.md §3 et §4.

import { defineStore } from "pinia"
import { reportsApi } from "~/services/api/reports"
import type {
  GenerateRequest,
  GenerationState,
  PreviewUrl,
  Rapport,
} from "~/types/reports"

interface ReportsStoreState {
  reports: Rapport[]
  pending: Record<string, GenerationState>
  loading: boolean
  error: string | null
  previewUrls: Record<
    string,
    { url: string; expiresAt: number } | undefined
  >
}

function emptyState(): ReportsStoreState {
  return {
    reports: [],
    pending: {},
    loading: false,
    error: null,
    previewUrls: {},
  }
}

export const useReportsStore = defineStore("reports", {
  state: (): ReportsStoreState => emptyState(),

  getters: {
    pendingList(state): GenerationState[] {
      return Object.values(state.pending).filter(
        (g) => g.phase === "pending" || g.phase === "running",
      )
    },
    byId: (state) => (id: string) =>
      state.reports.find((r) => r.id === id) ?? null,
  },

  actions: {
    async fetchAll(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        this.reports = await reportsApi.fetchAll()
      } catch (err: unknown) {
        this.error =
          err instanceof Error ? err.message : "reports.errors.fetch_failed"
      } finally {
        this.loading = false
      }
    },

    async generate(payload: GenerateRequest): Promise<string> {
      // Le backend F24 actuel renvoie le rapport prêt synchroniquement.
      // On crée néanmoins un GenerationState pour conserver le contrat F49
      // (pending → running → ready) côté UI.
      const tempId = `tmp-${Date.now()}`
      this.pending = {
        ...this.pending,
        [tempId]: {
          generation_id: tempId,
          phase: "pending",
          step: "queued",
          percent: 0,
          rapport_id: null,
          download_filename: null,
          error: null,
          last_event_id: 0,
          started_at: new Date().toISOString(),
        },
      }
      try {
        const rapport = await reportsApi.generate(payload)
        // Remplace l'entrée pending par l'id réel et la transitionne en ready
        const next = { ...this.pending }
        delete next[tempId]
        next[rapport.id] = {
          generation_id: rapport.id,
          phase: "ready",
          step: "done",
          percent: 100,
          rapport_id: rapport.id,
          download_filename: rapport.download_filename,
          error: null,
          last_event_id: 3,
          started_at: new Date().toISOString(),
        }
        this.pending = next
        // Insère ou met à jour le rapport
        const idx = this.reports.findIndex((r) => r.id === rapport.id)
        if (idx >= 0) {
          const arr = [...this.reports]
          arr[idx] = rapport
          this.reports = arr
        } else {
          this.reports = [rapport, ...this.reports]
        }
        return rapport.id
      } catch (err: unknown) {
        const next = { ...this.pending }
        const cur = next[tempId]
        if (cur) {
          next[tempId] = {
            ...cur,
            phase: "failed",
            error:
              err instanceof Error
                ? err.message
                : "reports.errors.generate_failed",
          }
        }
        this.pending = next
        throw err
      }
    },

    subscribeStream(generationId: string): void {
      // Réservé à un cas où le backend deviendrait réellement asynchrone.
      // Pour le MVP F49, `generate()` transitionne directement vers `ready`
      // et `useReportGenerationStream` ne fait que conserver la trace.
      const cur = this.pending[generationId]
      if (!cur) return
      if (cur.phase === "pending") {
        this.pending = {
          ...this.pending,
          [generationId]: { ...cur, phase: "running" },
        }
      }
    },

    cancelStream(generationId: string): void {
      const next = { ...this.pending }
      delete next[generationId]
      this.pending = next
    },

    applyStreamEvent(
      generationId: string,
      event: "progress" | "done" | "failed",
      data: { step?: string; percent?: number; rapport_id?: string; download_filename?: string; error?: string; eventId?: number },
    ): void {
      const cur = this.pending[generationId]
      if (!cur) return
      if (event === "progress") {
        this.pending = {
          ...this.pending,
          [generationId]: {
            ...cur,
            phase: "running",
            step: data.step ?? cur.step,
            percent: data.percent ?? cur.percent,
            last_event_id: data.eventId ?? cur.last_event_id,
          },
        }
      } else if (event === "done") {
        this.pending = {
          ...this.pending,
          [generationId]: {
            ...cur,
            phase: "ready",
            percent: 100,
            rapport_id: data.rapport_id ?? cur.rapport_id,
            download_filename:
              data.download_filename ?? cur.download_filename,
            last_event_id: data.eventId ?? cur.last_event_id,
          },
        }
      } else if (event === "failed") {
        this.pending = {
          ...this.pending,
          [generationId]: {
            ...cur,
            phase: "failed",
            error: data.error ?? "reports.errors.generation_failed",
            last_event_id: data.eventId ?? cur.last_event_id,
          },
        }
      }
    },

    async loadPreviewUrl(rapportId: string): Promise<PreviewUrl> {
      const cached = this.previewUrls[rapportId]
      const now = Date.now()
      // Marge 10 s pour éviter d'utiliser une URL au bord de l'expiration.
      if (cached && cached.expiresAt - 10_000 > now) {
        return {
          url: cached.url,
          expires_at: new Date(cached.expiresAt).toISOString(),
        }
      }
      const fresh = await reportsApi.loadPreviewUrl(rapportId)
      this.previewUrls = {
        ...this.previewUrls,
        [rapportId]: {
          url: fresh.url,
          expiresAt: new Date(fresh.expires_at).getTime(),
        },
      }
      return fresh
    },

    invalidatePreviewUrl(rapportId: string): void {
      const next = { ...this.previewUrls }
      delete next[rapportId]
      this.previewUrls = next
    },

    rehydratePending(): void {
      // FR-003a — au mount d'une page, ré-attache un `running` aux entrées
      // toujours `pending`/`running`. Avec le backend synchrone actuel, ces
      // entrées n'existent pas après un reload (état non persisté côté UI).
      // L'implémentation est volontairement triviale ; quand le backend
      // deviendra async, on la complétera avec un appel REST de reprise.
      const next = { ...this.pending }
      for (const [k, v] of Object.entries(next)) {
        if (v.phase === "pending") next[k] = { ...v, phase: "running" }
      }
      this.pending = next
    },

    reset(): void {
      Object.assign(this, emptyState())
    },
  },
})
