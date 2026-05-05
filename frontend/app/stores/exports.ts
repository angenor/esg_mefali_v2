// F52 US3 — Pinia store des exports historiques.
import { defineStore } from 'pinia'

export type ExportType =
  | 'rgpd_full'
  | 'report_pdf'
  | 'attestation_pdf'
  | 'dossier_pdf'

export type ExportStatus = 'pending' | 'ready' | 'expired' | 'failed'
export type ExportFormat = 'pdf' | 'json'
export type ExportDeliveredVia = 'inapp' | 'email'

export interface ExportItem {
  id: string
  type: ExportType
  format: ExportFormat
  size_bytes: number | null
  status: ExportStatus
  created_at: string
  ready_at: string | null
  signed_url: string | null
  signed_url_expires_at: string | null
  delivered_via: ExportDeliveredVia | null
}

export interface ExportCreateInput {
  type: ExportType
  format: ExportFormat
  report_id?: string | null
  attestation_id?: string | null
  candidature_id?: string | null
}

interface State {
  items: ExportItem[]
  loading: boolean
  creating: boolean
  error: string | null
  nextCursor: string | null
}

interface ListResponse {
  items: ExportItem[]
  next_cursor: string | null
}

export const useExportsStore = defineStore('exports', {
  state: (): State => ({
    items: [],
    loading: false,
    creating: false,
    error: null,
    nextCursor: null,
  }),
  getters: {
    byId: (s) => (id: string): ExportItem | undefined =>
      s.items.find((it) => it.id === id),
    readyCount: (s): number =>
      s.items.filter((it) => it.status === 'ready').length,
  },
  actions: {
    async load(opts?: { type?: ExportType[]; cursor?: string | null }): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const params = new URLSearchParams()
        for (const t of opts?.type ?? []) params.append('type', t)
        if (opts?.cursor) params.append('cursor', opts.cursor)
        const qs = params.toString()
        const url = `${apiBase}/me/exports${qs ? `?${qs}` : ''}`
        const data = await $fetch<ListResponse>(url, { credentials: 'include' })
        const incoming = Array.isArray(data?.items) ? data.items : []
        this.items = opts?.cursor ? [...this.items, ...incoming] : incoming
        this.nextCursor = data?.next_cursor ?? null
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'load_failed'
      } finally {
        this.loading = false
      }
    },
    async create(input: ExportCreateInput): Promise<ExportItem | null> {
      this.creating = true
      this.error = null
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const { withCsrf } = useCsrf()
        const data = await $fetch<ExportItem>(`${apiBase}/me/exports`, {
          method: 'POST',
          credentials: 'include',
          headers: withCsrf(),
          body: input,
        })
        if (data && data.id) {
          // Insertion en tête de liste (DESC par created_at).
          this.items = [data, ...this.items.filter((it) => it.id !== data.id)]
        }
        return data
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'create_failed'
        return null
      } finally {
        this.creating = false
      }
    },
    async refreshOne(id: string): Promise<void> {
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const data = await $fetch<ExportItem>(`${apiBase}/me/exports/${id}`, {
          credentials: 'include',
        })
        if (data && data.id) {
          this.items = this.items.map((it) => (it.id === data.id ? data : it))
        }
      } catch {
        // Best-effort polling — error noté seulement si on n'a aucun item.
      }
    },
    handleSseSystemEvent(payload: { export_id?: string }): void {
      if (!payload?.export_id) return
      void this.refreshOne(payload.export_id)
    },
    reset(): void {
      this.items = []
      this.nextCursor = null
      this.error = null
    },
  },
})
