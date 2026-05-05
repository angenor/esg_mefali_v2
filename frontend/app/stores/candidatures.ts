// F51 T014 — Store Pinia useCandidaturesStore.
//
// Source de vérité UI pour `/candidatures`, `/candidatures/[id]` et le wizard.
// Émet les événements P8 via `~/lib/candidatureEvents`.

import { defineStore } from "pinia"
import { candidaturesApi } from "~/services/api/candidatures"
import { emitCandidatureEvent } from "~/lib/candidatureEvents"
import type {
  CandidatureDetail,
  CandidatureRow,
  WizardDraftPatch,
  WizardSubmitIn,
} from "~/types/candidatures"

export type SaveStatus = "idle" | "saving" | "saved" | "offline" | "error"

interface State {
  list: CandidatureRow[]
  detail: CandidatureDetail | null
  loading: boolean
  error: string | null
  saveStatus: SaveStatus
  saveError: string | null
  lastSavedAt: number | null
}

export const useCandidaturesStore = defineStore("candidatures", {
  state: (): State => ({
    list: [],
    detail: null,
    loading: false,
    error: null,
    saveStatus: "idle",
    saveError: null,
    lastSavedAt: null,
  }),

  getters: {
    drafts: (s) => s.list.filter((c) => c.statut === "brouillon"),
    submitted: (s) => s.list.filter((c) => c.statut !== "brouillon"),
  },

  actions: {
    async fetchList(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        this.list = await candidaturesApi.list()
      } catch (err) {
        this.error = (err as Error).message ?? "fetch_failed"
      } finally {
        this.loading = false
      }
    },

    async fetchDetail(id: string): Promise<void> {
      this.loading = true
      this.error = null
      try {
        this.detail = await candidaturesApi.getDetail(id)
      } catch (err) {
        this.error = (err as Error).message ?? "fetch_detail_failed"
        this.detail = null
      } finally {
        this.loading = false
      }
    },

    async create(projetId: string, offreId: string): Promise<string | null> {
      try {
        const r = await candidaturesApi.create(projetId, offreId)
        emitCandidatureEvent("candidature:updated", {
          candidature_id: r.id,
          version: 1,
        })
        return r.id
      } catch (err) {
        this.error = (err as Error).message ?? "create_failed"
        return null
      }
    },

    async patchDraft(id: string, patch: WizardDraftPatch): Promise<void> {
      this.saveStatus = "saving"
      this.saveError = null
      try {
        const out = await candidaturesApi.patchDraft(id, patch)
        if (this.detail && this.detail.id === id) {
          this.detail.step_courant = out.step_courant
          this.detail.progression_pct = out.progression_pct
          this.detail.draft_snapshot_json = out.draft_snapshot_json
          this.detail.version = out.version
        }
        this.saveStatus = "saved"
        this.lastSavedAt = Date.now()
        emitCandidatureEvent("candidature:updated", {
          candidature_id: id,
          version: out.version,
        })
        if (patch.step_courant !== undefined) {
          emitCandidatureEvent("wizard:step:changed", {
            candidature_id: id,
            from: this.detail?.step_courant ?? 0,
            to: out.step_courant,
          })
        }
      } catch (err) {
        const e = err as Error & { statusCode?: number }
        if (e.statusCode === 409) {
          this.saveStatus = "error"
          this.saveError = "version_conflict"
        } else if (typeof navigator !== "undefined" && !navigator.onLine) {
          this.saveStatus = "offline"
          this.saveError = "offline"
        } else {
          this.saveStatus = "error"
          this.saveError = e.message ?? "save_failed"
        }
        throw err
      }
    },

    async submit(id: string, body: WizardSubmitIn): Promise<boolean> {
      this.error = null
      try {
        const out = await candidaturesApi.submit(id, body)
        if (this.detail && this.detail.id === id) {
          this.detail.statut = "soumise"
          this.detail.submitted_at = out.submitted_at
          this.detail.version = out.version
        }
        emitCandidatureEvent("candidature:updated", {
          candidature_id: id,
          version: out.version,
        })
        return true
      } catch (err) {
        this.error = (err as Error).message ?? "submit_failed"
        return false
      }
    },

    reset(): void {
      this.detail = null
      this.error = null
      this.saveStatus = "idle"
      this.saveError = null
      this.lastSavedAt = null
    },
  },
})
