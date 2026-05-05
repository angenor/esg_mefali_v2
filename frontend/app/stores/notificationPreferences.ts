// F52 US2 — Préférences de notifications (kind × channel).
import { defineStore } from 'pinia'
import type { NotificationKind } from '~/stores/notifications'

export type NotificationChannel = 'email' | 'in_app'

export interface NotificationPreferenceItem {
  kind: NotificationKind
  channel: NotificationChannel
  enabled: boolean
}

interface State {
  items: NotificationPreferenceItem[]
  loading: boolean
  saving: boolean
  error: string | null
  pendingPatches: NotificationPreferenceItem[]
  debounceTimer: ReturnType<typeof setTimeout> | null
}

const DEBOUNCE_MS = 300

export const useNotificationPreferencesStore = defineStore(
  'notificationPreferences',
  {
    state: (): State => ({
      items: [],
      loading: false,
      saving: false,
      error: null,
      pendingPatches: [],
      debounceTimer: null,
    }),
    getters: {
      isEnabled:
        (s) =>
        (kind: NotificationKind, channel: NotificationChannel): boolean => {
          const row = s.items.find(
            (i) => i.kind === kind && i.channel === channel
          )
          return row ? row.enabled : true
        },
    },
    actions: {
      async load(): Promise<void> {
        this.loading = true
        this.error = null
        try {
          const config = useRuntimeConfig()
          const apiBase = config.public.apiBase as string
          const data = await $fetch<{ items: NotificationPreferenceItem[] }>(
            `${apiBase}/me/notification-preferences`,
            { credentials: 'include' }
          )
          this.items = Array.isArray(data?.items) ? data.items : []
        } catch (err) {
          this.error = err instanceof Error ? err.message : 'load_failed'
        } finally {
          this.loading = false
        }
      },
      togglePreference(
        kind: NotificationKind,
        channel: NotificationChannel,
        enabled: boolean
      ): void {
        // Mise à jour optimiste locale.
        const existingIdx = this.items.findIndex(
          (i) => i.kind === kind && i.channel === channel
        )
        if (existingIdx >= 0) {
          const next = [...this.items]
          next[existingIdx] = { ...next[existingIdx], enabled }
          this.items = next
        } else {
          this.items = [...this.items, { kind, channel, enabled }]
        }
        // Cumule les patches puis flush en debounce.
        const remaining = this.pendingPatches.filter(
          (p) => !(p.kind === kind && p.channel === channel)
        )
        this.pendingPatches = [...remaining, { kind, channel, enabled }]
        if (this.debounceTimer) clearTimeout(this.debounceTimer)
        this.debounceTimer = setTimeout(() => {
          void this.flush()
        }, DEBOUNCE_MS)
      },
      async flush(): Promise<void> {
        if (this.pendingPatches.length === 0) return
        const updates = this.pendingPatches
        this.pendingPatches = []
        this.saving = true
        try {
          const config = useRuntimeConfig()
          const apiBase = config.public.apiBase as string
          const { withCsrf } = useCsrf()
          const data = await $fetch<{ items: NotificationPreferenceItem[] }>(
            `${apiBase}/me/notification-preferences`,
            {
              method: 'PATCH',
              credentials: 'include',
              headers: withCsrf(),
              body: { updates },
            }
          )
          this.items = data?.items ?? this.items
        } catch (err) {
          this.error = err instanceof Error ? err.message : 'patch_failed'
          // En cas d'échec on recharge depuis le serveur pour rester cohérent.
          await this.load()
        } finally {
          this.saving = false
        }
      },
      reset(): void {
        this.items = []
        this.pendingPatches = []
        this.error = null
        if (this.debounceTimer) clearTimeout(this.debounceTimer)
        this.debounceTimer = null
      },
    },
  }
)
