// F52 US2 — Sessions actives + révocation.
import { defineStore } from 'pinia'

export interface SessionItem {
  id: string
  device_label: string
  ip_country: string | null
  user_agent_summary: string | null
  created_at: string
  last_seen_at: string
  is_current: boolean
}

interface State {
  items: SessionItem[]
  loading: boolean
  error: string | null
}

export const useSessionsStore = defineStore('sessions', {
  state: (): State => ({ items: [], loading: false, error: null }),
  actions: {
    async load(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const data = await $fetch<{ items: SessionItem[] }>(
          `${apiBase}/me/sessions`,
          { credentials: 'include' }
        )
        this.items = Array.isArray(data?.items) ? data.items : []
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'load_failed'
      } finally {
        this.loading = false
      }
    },
    async revoke(id: string): Promise<void> {
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const { withCsrf } = useCsrf()
        await $fetch(`${apiBase}/me/sessions/${id}`, {
          method: 'DELETE',
          credentials: 'include',
          headers: withCsrf(),
        })
        this.items = this.items.filter((s) => s.id !== id)
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'revoke_failed'
        throw err
      }
    },
  },
})
