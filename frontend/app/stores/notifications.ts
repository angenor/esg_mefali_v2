// F38 T011 — Pinia store notifications
import { defineStore } from 'pinia'

export type NotificationKind =
  | 'system'
  | 'candidature'
  | 'scoring'
  | 'attestation'
  | 'plan_action'
  | 'admin'

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
  'system',
  'candidature',
  'scoring',
  'attestation',
  'plan_action',
  'admin',
])

const MAX_ITEMS = 50

interface State {
  items: Notification[]
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

export const useNotificationsStore = defineStore('notifications', {
  state: (): State => ({
    items: [],
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
    async markAllRead(): Promise<void> {
      const ids = this.items.filter((n) => !n.read_at).map((n) => n.id)
      await Promise.all(ids.map((id) => this.markRead(id)))
    },
    setStreamConnected(connected: boolean): void {
      this.isStreamConnected = connected
    },
    reset(): void {
      this.items = []
      this.isStreamConnected = false
      this.lastSyncedAt = null
      this.loadError = null
    },
  },
})
