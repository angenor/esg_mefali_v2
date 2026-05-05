// F52 US2 — Consentements RGPD (lecture + retrait).
import { defineStore } from 'pinia'

export interface ConsentItem {
  id: string
  category: string
  label: string
  given_at: string | null
  withdrawn_at: string | null
}

interface State {
  items: ConsentItem[]
  loading: boolean
  error: string | null
}

export const useConsentsStore = defineStore('consents', {
  state: (): State => ({ items: [], loading: false, error: null }),
  actions: {
    async load(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const data = await $fetch<{ items?: ConsentItem[] } | ConsentItem[]>(
          `${apiBase}/me/consents`,
          { credentials: 'include' }
        )
        if (Array.isArray(data)) this.items = data
        else this.items = data?.items ?? []
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'load_failed'
      } finally {
        this.loading = false
      }
    },
    async withdraw(id: string): Promise<void> {
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const { withCsrf } = useCsrf()
        await $fetch(`${apiBase}/me/consents/${id}/withdraw`, {
          method: 'POST',
          credentials: 'include',
          headers: withCsrf(),
        })
        await this.load()
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'withdraw_failed'
        throw err
      }
    },
  },
})
