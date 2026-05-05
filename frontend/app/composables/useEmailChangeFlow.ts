// F52 US2 — Composable du flow changement d'e-mail.
import { ref } from 'vue'

interface State {
  loading: boolean
  pendingEmail: string | null
  sentAt: string | null
  error: string | null
}

export function useEmailChangeFlow() {
  const state = ref<State>({
    loading: false,
    pendingEmail: null,
    sentAt: null,
    error: null,
  })

  async function requestChange(payload: {
    new_email: string
    current_password: string
  }): Promise<void> {
    state.value.loading = true
    state.value.error = null
    try {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      const { withCsrf } = useCsrf()
      const data = await $fetch<{
        email_pending: string
        verification_sent_at: string
      }>(`${apiBase}/me/email-change`, {
        method: 'POST',
        credentials: 'include',
        headers: withCsrf(),
        body: payload,
      })
      state.value.pendingEmail = data.email_pending
      state.value.sentAt = data.verification_sent_at
    } catch (err: unknown) {
      const e = err as { data?: { detail?: { code?: string } } }
      state.value.error = e?.data?.detail?.code ?? 'request_failed'
      throw err
    } finally {
      state.value.loading = false
    }
  }

  async function verifyToken(token: string): Promise<string> {
    state.value.loading = true
    state.value.error = null
    try {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      const { withCsrf } = useCsrf()
      const data = await $fetch<{ email: string }>(
        `${apiBase}/me/email-change/verify`,
        {
          method: 'POST',
          credentials: 'include',
          headers: withCsrf(),
          query: { token },
        }
      )
      state.value.pendingEmail = null
      return data.email
    } catch (err: unknown) {
      const e = err as { data?: { detail?: { code?: string } } }
      state.value.error = e?.data?.detail?.code ?? 'verify_failed'
      throw err
    } finally {
      state.value.loading = false
    }
  }

  return { state, requestChange, verifyToken }
}
