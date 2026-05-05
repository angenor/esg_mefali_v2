// F38 + F52 — Pinia store notifications
// F52 US1 : filtres, mark-all-read optimiste avec rollback, bulk_read SSE.
import { defineStore } from 'pinia'

export type NotificationKind =
  | 'deadline_j_minus_30'
  | 'deadline_j_minus_7'
  | 'deadline_j_minus_1'
  | 'candidature_inactive'
  | 'offre_recommandee'
  | 'system'

export interface Notification {
  id: string
  kind: NotificationKind
  title: string
  body?: string
  link?: string
  created_at: string
  read_at: string | null
}

const VALID_KINDS: ReadonlySet<NotificationKind> = new Set([
  'deadline_j_minus_30',
  'deadline_j_minus_7',
  'deadline_j_minus_1',
  'candidature_inactive',
  'offre_recommandee',
  'system',
])

const MAX_ITEMS = 50

export interface NotificationFilters {
  unreadOnly: boolean
  kinds: NotificationKind[]
  from: string | null
  to: string | null
}

interface State {
  items: Notification[]
  filters: NotificationFilters
  isStreamConnected: boolean
  lastSyncedAt: Date | null
  loadError: Error | null
}

function isValid(item: unknown): item is Notification {
  if (!item || typeof item !== 'object') return false
  const n = item as Notification
  return (
    typeof n.id === 'string' &&
    typeof n.title === 'string' &&
    typeof n.created_at === 'string' &&
    VALID_KINDS.has(n.kind as NotificationKind)
  )
}

function trimToCap(items: Notification[]): Notification[] {
  if (items.length <= MAX_ITEMS) return items
  return [...items]
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
    .slice(0, MAX_ITEMS)
}

function defaultFilters(): NotificationFilters {
  return {
    unreadOnly: false,
    kinds: [],
    from: null,
    to: null,
  }
}

export const useNotificationsStore = defineStore('notifications', {
  state: (): State => ({
    items: [],
    filters: defaultFilters(),
    isStreamConnected: false,
    lastSyncedAt: null,
    loadError: null,
  }),
  getters: {
    unreadCount: (s): number => s.items.filter((n) => !n.read_at).length,
    latestUnread: (s): Notification[] =>
      [...s.items]
        .filter((n) => !n.read_at)
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
        .slice(0, 5),
    filteredItems: (s): Notification[] => {
      const { unreadOnly, kinds, from, to } = s.filters
      return s.items.filter((n) => {
        if (unreadOnly && n.read_at) return false
        if (kinds.length > 0 && !kinds.includes(n.kind)) return false
        if (from && n.created_at < from) return false
        if (to && n.created_at > to) return false
        return true
      })
    },
  },
  actions: {
    async loadInitial(): Promise<void> {
      if (typeof window === 'undefined') return
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const data = await $fetch<Notification[]>(`${apiBase}/me/notifications`, {
          credentials: 'include',
        })
        this.items = trimToCap((Array.isArray(data) ? data : []).filter(isValid))
        this.lastSyncedAt = new Date()
        this.loadError = null
      } catch (err) {
        this.loadError = err instanceof Error ? err : new Error('load failed')
      }
    },
    setFilters(patch: Partial<NotificationFilters>): void {
      this.filters = { ...this.filters, ...patch }
    },
    resetFilters(): void {
      this.filters = defaultFilters()
    },
    pushFromStream(evt: unknown): void {
      if (!isValid(evt)) return
      const idx = this.items.findIndex((n) => n.id === evt.id)
      const next = [...this.items]
      if (idx >= 0) {
        next[idx] = evt
      } else {
        next.unshift(evt)
      }
      this.items = trimToCap(next)
    },
    applyBulkReadFromStream(payload: { kinds?: NotificationKind[] | null; count?: number }): void {
      const restrictTo = Array.isArray(payload.kinds) && payload.kinds.length > 0
        ? new Set(payload.kinds)
        : null
      const now = new Date().toISOString()
      this.items = this.items.map((n) => {
        if (n.read_at) return n
        if (restrictTo && !restrictTo.has(n.kind)) return n
        return { ...n, read_at: now }
      })
    },
    async markRead(id: string): Promise<void> {
      const target = this.items.find((n) => n.id === id)
      if (!target || target.read_at) return
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const { withCsrf } = useCsrf()
        await $fetch(`${apiBase}/me/notifications/${id}/read`, {
          method: 'PATCH',
          credentials: 'include',
          headers: withCsrf(),
        })
        this.items = this.items.map((n) =>
          n.id === id ? { ...n, read_at: new Date().toISOString() } : n
        )
      } catch (err) {
        this.loadError = err instanceof Error ? err : new Error('mark read failed')
      }
    },
    async markAllReadOptimistic(kinds?: NotificationKind[]): Promise<{
      updated_count: number
      unread_count_after: number
    }> {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      const { withCsrf } = useCsrf()

      // Snapshot avant mutation pour rollback en cas d'échec.
      const snapshot = this.items.map((n) => ({ ...n }))
      const restrictTo = kinds && kinds.length > 0 ? new Set(kinds) : null
      const now = new Date().toISOString()

      this.items = this.items.map((n) => {
        if (n.read_at) return n
        if (restrictTo && !restrictTo.has(n.kind)) return n
        return { ...n, read_at: now }
      })

      try {
        const body: { kinds?: NotificationKind[] } = {}
        if (kinds && kinds.length > 0) body.kinds = kinds
        const resp = await $fetch<{
          updated_count: number
          unread_count_after: number
        }>(`${apiBase}/me/notifications/read-all`, {
          method: 'POST',
          credentials: 'include',
          headers: withCsrf(),
          body,
        })
        return resp
      } catch (err) {
        // Rollback
        this.items = snapshot
        this.loadError = err instanceof Error ? err : new Error('mark all read failed')
        throw err
      }
    },
    async markAllRead(): Promise<void> {
      // Compat F38 — délégué à la version optimiste batch.
      await this.markAllReadOptimistic()
    },
    setStreamConnected(connected: boolean): void {
      this.isStreamConnected = connected
    },
    reset(): void {
      this.items = []
      this.filters = defaultFilters()
      this.isStreamConnected = false
      this.lastSyncedAt = null
      this.loadError = null
    },
  },
})
