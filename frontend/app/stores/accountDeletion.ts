// F52 US2 — Demande de suppression de compte (J+30).
import { defineStore } from 'pinia'

export interface AccountDeletionRequest {
  id: string
  status: 'pending' | 'cancelled' | 'executed'
  requested_at: string
  scheduled_for: string
  can_cancel: boolean
}

interface State {
  request: AccountDeletionRequest | null
  loading: boolean
  saving: boolean
  error: string | null
}

export const useAccountDeletionStore = defineStore('accountDeletion', {
  state: (): State => ({
    request: null,
    loading: false,
    saving: false,
    error: null,
  }),
  getters: {
    isPending: (s) => s.request !== null && s.request.status === 'pending',
  },
  actions: {
    async load(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const data = await $fetch<{ request: AccountDeletionRequest | null }>(
          `${apiBase}/me/account-deletion`,
          { credentials: 'include' }
        )
        this.request = data?.request ?? null
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'load_failed'
      } finally {
        this.loading = false
      }
    },
    async create(payload: {
      confirmation_text: string
      reason_motif?: string | null
    }): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const { withCsrf } = useCsrf()
        const data = await $fetch<{ request: AccountDeletionRequest }>(
          `${apiBase}/me/account-deletion`,
          {
            method: 'POST',
            credentials: 'include',
            headers: withCsrf(),
            body: payload,
          }
        )
        this.request = data?.request ?? null
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'create_failed'
        throw err
      } finally {
        this.saving = false
      }
    },
    async cancel(): Promise<void> {
      if (!this.request) return
      this.saving = true
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const { withCsrf } = useCsrf()
        await $fetch(`${apiBase}/me/account-deletion/${this.request.id}`, {
          method: 'DELETE',
          credentials: 'include',
          headers: withCsrf(),
        })
        this.request = null
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'cancel_failed'
        throw err
      } finally {
        this.saving = false
      }
    },
  },
})
