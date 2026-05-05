// F50 T010 + T030 + T040 — Store Pinia useDocumentsStore.
// Cf. specs/050-documents-ocr-ui/contracts/documents_ui_contracts.md §8.

import { defineStore } from "pinia"
import { documentsApi } from "~/services/api/documents"
import { documentEvents } from "~/lib/documentEvents"
import { useFileFingerprint } from "~/composables/useFileFingerprint"
import { useOcrPolling } from "~/composables/useOcrPolling"
import type {
  DocumentDetail,
  DocumentListItem,
  UploadJob,
  UploadJobStatus,
  ValidateExtractionIn,
} from "~/types/documents"

interface SearchState {
  q: string
  type: string | null
  from: string | null
  to: string | null
}

interface DocumentsState {
  items: Record<string, DocumentDetail>
  byEntreprise: string[]
  byProjet: Record<string, string[]>
  uploadQueue: UploadJob[]
  pollingStops: Record<string, () => void>
  search: SearchState
  loading: boolean
  error: string | null
}

const QUEUE_PARALLELISM = 5

function genJobId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return `job_${Math.random().toString(36).slice(2)}_${Date.now()}`
}

function listItemFromDetail(d: DocumentDetail): DocumentListItem {
  return {
    id: d.id,
    name: d.name,
    mime_type: d.mime_type,
    size_bytes: d.size_bytes,
    type: d.type,
    created_at: d.created_at,
    ocr_status: d.ocr_status,
    extraction_validated_at: d.extraction_validated_at,
    tags: d.tags ?? [],
    source: "document_entreprise",
  }
}

function listItemAsDetailStub(li: DocumentListItem): DocumentDetail {
  return {
    id: li.id,
    entreprise_id: "",
    name: li.name,
    original_filename: li.name,
    mime_type: li.mime_type,
    size_bytes: li.size_bytes,
    type: li.type,
    ocr_status: li.ocr_status,
    ocr_error: null,
    created_at: li.created_at,
    extraction_payload: { fields: [] },
    extraction_validated_at: li.extraction_validated_at,
    extraction_validated_by: null,
    linked_projets: [],
    tags: li.tags ?? [],
    deleted_at: null,
    purge_scheduled_at: null,
  }
}

function normalize(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
}

export const useDocumentsStore = defineStore("documents-f50", {
  state: (): DocumentsState => ({
    items: {},
    byEntreprise: [],
    byProjet: {},
    uploadQueue: [],
    pollingStops: {},
    search: { q: "", type: null, from: null, to: null },
    loading: false,
    error: null,
  }),

  getters: {
    entrepriseList(state): DocumentDetail[] {
      return state.byEntreprise.map((id) => state.items[id]).filter(Boolean) as DocumentDetail[]
    },

    filteredItems(state): DocumentDetail[] {
      const all = state.byEntreprise
        .map((id) => state.items[id])
        .filter((d): d is DocumentDetail => Boolean(d))
      const { q, type, from, to } = state.search
      const qNorm = q ? normalize(q) : ""
      return all.filter((d) => {
        if (type && d.type !== type) return false
        if (qNorm) {
          const hay = normalize(`${d.name} ${(d.tags ?? []).join(" ")}`)
          if (!hay.includes(qNorm)) return false
        }
        if (from && d.created_at < from) return false
        if (to && d.created_at > to) return false
        return true
      })
    },

    activeUploads(state): UploadJob[] {
      return state.uploadQueue.filter(
        (j) => j.status !== "success" && j.status !== "cancelled" && j.status !== "error",
      )
    },

    countByStatus(state): Record<string, number> {
      const counts: Record<string, number> = {}
      for (const id of state.byEntreprise) {
        const d = state.items[id]
        if (!d) continue
        counts[d.ocr_status] = (counts[d.ocr_status] ?? 0) + 1
      }
      return counts
    },
  },

  actions: {
    upsert(doc: DocumentDetail): void {
      this.items[doc.id] = doc
      if (!this.byEntreprise.includes(doc.id)) {
        this.byEntreprise = [doc.id, ...this.byEntreprise]
      }
    },

    setSearch(patch: Partial<SearchState>): void {
      this.search = { ...this.search, ...patch }
    },

    async fetchEntreprise(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const list = await documentsApi.listEntrepriseDocuments()
        this.byEntreprise = list.map((l) => l.id)
        for (const li of list) {
          const existing = this.items[li.id]
          this.items[li.id] = existing
            ? { ...existing, ...listItemAsDetailStub(li) }
            : listItemAsDetailStub(li)
        }
      } catch (e) {
        this.error = (e as Error).message ?? "fetch_failed"
        throw e
      } finally {
        this.loading = false
      }
    },

    async fetchProjet(projetId: string): Promise<void> {
      const list = await documentsApi.listProjetDocuments(projetId)
      this.byProjet[projetId] = list.map((l) => l.id)
      for (const li of list) {
        if (!this.items[li.id]) {
          this.items[li.id] = listItemAsDetailStub(li)
        }
      }
    },

    setJobStatus(jobId: string, patch: Partial<UploadJob>): void {
      const idx = this.uploadQueue.findIndex((j) => j.id === jobId)
      if (idx === -1) return
      this.uploadQueue[idx] = { ...this.uploadQueue[idx]!, ...patch }
    },

    removeJob(jobId: string): void {
      this.uploadQueue = this.uploadQueue.filter((j) => j.id !== jobId)
    },

    async enqueueUpload(
      file: File,
      opts: { type: string; linkProjetId?: string | null; forceNew?: boolean } = {
        type: "autre",
      },
    ): Promise<UploadJob> {
      const job: UploadJob = {
        id: genJobId(),
        file,
        filename: file.name,
        size: file.size,
        mime: file.type || "application/octet-stream",
        sha256: null,
        percent: 0,
        status: "pending" as UploadJobStatus,
        linkProjetId: opts.linkProjetId ?? null,
      }
      this.uploadQueue = [...this.uploadQueue, job]
      // Lance le démarrage si la queue n'est pas saturée.
      void this.processQueue(opts)
      return job
    },

    async processQueue(opts: {
      type: string
      linkProjetId?: string | null
      forceNew?: boolean
    }): Promise<void> {
      const running = this.uploadQueue.filter(
        (j) => j.status === "uploading" || j.status === "fingerprinting",
      ).length
      if (running >= QUEUE_PARALLELISM) return
      const next = this.uploadQueue.find((j) => j.status === "pending")
      if (!next) return
      void this.runJob(next, opts)
      // Continue en boucle pour saturer la queue (max 5).
      void this.processQueue(opts)
    },

    async runJob(
      job: UploadJob,
      opts: { type: string; linkProjetId?: string | null; forceNew?: boolean },
    ): Promise<void> {
      const { computeSha256 } = useFileFingerprint()
      try {
        this.setJobStatus(job.id, { status: "fingerprinting" })
        const sha = await computeSha256(job.file)
        this.setJobStatus(job.id, { sha256: sha })

        if (!opts.forceNew) {
          const existing = await documentsApi.getByFingerprint(sha)
          if (existing) {
            this.setJobStatus(job.id, { status: "duplicate" })
            return
          }
        }

        this.setJobStatus(job.id, { status: "uploading", percent: 0 })
        const doc = await documentsApi.uploadDocument(job.file, {
          type: opts.type,
          name: job.filename,
          clientSha256: sha,
          linkProjetId: opts.linkProjetId ?? null,
          onProgress: (pct) => this.setJobStatus(job.id, { percent: pct }),
        })
        this.upsert(doc)
        this.setJobStatus(job.id, {
          status: "success",
          percent: 100,
          documentId: doc.id,
        })
        documentEvents.emit("documents:created", { document: doc })
        // Démarre polling si pas terminal.
        if (doc.ocr_status !== "done" && doc.ocr_status !== "error") {
          this.startPolling(doc.id)
        }
      } catch (e) {
        this.setJobStatus(job.id, {
          status: "error",
          error: (e as Error).message ?? "upload_failed",
        })
      } finally {
        // Lance la suite.
        void this.processQueue(opts)
      }
    },

    confirmDuplicateReuse(jobId: string): void {
      const job = this.uploadQueue.find((j) => j.id === jobId)
      if (!job) return
      this.setJobStatus(jobId, { status: "cancelled" })
    },

    confirmDuplicateForceNew(jobId: string, opts: { type: string }): void {
      const job = this.uploadQueue.find((j) => j.id === jobId)
      if (!job) return
      this.setJobStatus(jobId, { status: "pending" })
      void this.processQueue({ ...opts, forceNew: true })
    },

    startPolling(docId: string): void {
      if (this.pollingStops[docId]) return
      const polling = useOcrPolling((id) => documentsApi.getDocument(id))
      const handle = polling.start(docId, {
        onUpdate: (doc) => {
          this.upsert(doc)
          documentEvents.emit("documents:status-changed", {
            documentId: doc.id,
            ocrStatus: doc.ocr_status,
          })
        },
        onTimeout: (id) => {
          documentEvents.emit("documents:status-changed", {
            documentId: id,
            ocrStatus: "timeout",
          })
        },
      })
      this.pollingStops[docId] = handle.stop
    },

    stopPolling(docId: string): void {
      const stop = this.pollingStops[docId]
      if (stop) {
        stop()
        delete this.pollingStops[docId]
      }
    },

    stopAllPolling(): void {
      for (const [id, stop] of Object.entries(this.pollingStops)) {
        stop()
        delete this.pollingStops[id]
      }
    },

    async validateExtraction(
      docId: string,
      payload: ValidateExtractionIn,
    ): Promise<void> {
      const result = await documentsApi.validateExtraction(docId, payload)
      const existing = this.items[docId]
      if (existing) {
        const updated: DocumentDetail = {
          ...existing,
          extraction_validated_at: result.extraction_validated_at,
          extraction_validated_by: result.extraction_validated_by,
        }
        this.items[docId] = updated
        documentEvents.emit("documents:validated", { document: updated })
      }
    },

    async softDelete(docId: string): Promise<void> {
      // Optimiste : retirer immédiatement.
      this.byEntreprise = this.byEntreprise.filter((id) => id !== docId)
      try {
        await documentsApi.softDelete(docId)
        delete this.items[docId]
        documentEvents.emit("documents:deleted", { documentId: docId })
      } catch (e) {
        // Restaurer si échec.
        if (this.items[docId]) this.byEntreprise = [docId, ...this.byEntreprise]
        throw e
      }
    },

    async linkProjet(docId: string, projetId: string): Promise<void> {
      await documentsApi.linkProjet(docId, projetId)
      const doc = this.items[docId]
      if (doc && !doc.linked_projets.includes(projetId)) {
        this.items[docId] = {
          ...doc,
          linked_projets: [...doc.linked_projets, projetId],
        }
      }
      documentEvents.emit("documents:linked-projet", { documentId: docId, projetId })
    },

    async unlinkProjet(docId: string, projetId: string): Promise<void> {
      await documentsApi.unlinkProjet(docId, projetId)
      const doc = this.items[docId]
      if (doc) {
        this.items[docId] = {
          ...doc,
          linked_projets: doc.linked_projets.filter((p) => p !== projetId),
        }
      }
      documentEvents.emit("documents:unlinked-projet", {
        documentId: docId,
        projetId,
      })
    },

    async updateTags(docId: string, tags: string[]): Promise<void> {
      const updated = await documentsApi.updateTags(docId, tags)
      this.items[docId] = { ...(this.items[docId] ?? updated), tags: updated.tags }
    },

    async relaunchOcr(
      docId: string,
      opts: { invalidateValidation: boolean } = { invalidateValidation: false },
    ): Promise<void> {
      await documentsApi.relaunchOcr(docId, opts.invalidateValidation)
      const doc = this.items[docId]
      if (doc) {
        this.items[docId] = {
          ...doc,
          ocr_status: "processing",
          extraction_validated_at: opts.invalidateValidation
            ? null
            : doc.extraction_validated_at,
        }
      }
      this.startPolling(docId)
    },
  },
})

export { listItemFromDetail }
