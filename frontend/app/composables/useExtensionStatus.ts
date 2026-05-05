// F52 US5 — Statut extension navigateur côté app web.
import { ref } from 'vue'

export interface ExtensionStatus {
  detected: boolean
  extension_version: string | null
  last_ping_at: string | null
}

interface State {
  loading: boolean
  status: ExtensionStatus
  error: string | null
}

const DEFAULT_STATUS: ExtensionStatus = {
  detected: false,
  extension_version: null,
  last_ping_at: null,
}

export function useExtensionStatus() {
  const state = ref<State>({
    loading: false,
    status: { ...DEFAULT_STATUS },
    error: null,
  })

  async function refresh(): Promise<void> {
    state.value.loading = true
    state.value.error = null
    try {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      const data = await $fetch<ExtensionStatus>(
        `${apiBase}/me/extension/status`,
        { credentials: 'include' }
      )
      state.value.status = {
        detected: Boolean(data?.detected),
        extension_version: data?.extension_version ?? null,
        last_ping_at: data?.last_ping_at ?? null,
      }
    } catch (err) {
      state.value.error = err instanceof Error ? err.message : 'load_failed'
    } finally {
      state.value.loading = false
    }
  }

  async function forcePing(): Promise<void> {
    // Délègue au service worker via chrome.runtime si disponible.
    const c = (globalThis as unknown as {
      chrome?: { runtime?: { sendMessage?: (msg: unknown) => Promise<unknown> } }
    }).chrome
    if (c?.runtime?.sendMessage) {
      try {
        await c.runtime.sendMessage({ type: 'FORCE_PING', payload: {} })
        // Laisse au worker le temps de poster avant rafraîchissement.
        setTimeout(() => {
          void refresh()
        }, 500)
        return
      } catch {
        // L'extension n'est pas installée ou ne répond pas — on tente
        // un POST direct vers le backend pour signaler la présence côté
        // application (au moins on teste le réseau).
      }
    }
    // Pas de chrome runtime → fallback : ping direct via l'API.
    try {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      const { withCsrf } = useCsrf()
      await $fetch(`${apiBase}/me/extension/ping`, {
        method: 'POST',
        credentials: 'include',
        headers: withCsrf(),
        body: {
          extension_version: '0.0.0',
          user_agent_summary: 'web-fallback',
        },
      })
    } catch {
      // best-effort — l'erreur est surfaçée par refresh()
    }
    await refresh()
  }

  return { state, refresh, forcePing }
}
