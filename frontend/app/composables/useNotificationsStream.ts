// F38 T058 — useNotificationsStream (SSE + fallback polling)
import { readonly, ref, type Ref } from 'vue'
import { useNotificationsStore } from '~/stores/notifications'

interface NotificationsStream {
  start: () => void
  stop: () => void
  isConnected: Readonly<Ref<boolean>>
}

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 30000]
const POLLING_INTERVAL_MS = 60000

let instance: NotificationsStream | null = null

export function useNotificationsStream(): NotificationsStream {
  if (instance) return instance

  const isConnected = ref(false)
  let source: EventSource | null = null
  let pollingId: ReturnType<typeof setInterval> | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempt = 0
  let stopped = true

  function clearReconnectTimer(): void {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function clearPolling(): void {
    if (pollingId) {
      clearInterval(pollingId)
      pollingId = null
    }
  }

  function startPolling(): void {
    if (pollingId) return
    const store = useNotificationsStore()
    pollingId = setInterval(() => {
      void store.loadInitial()
    }, POLLING_INTERVAL_MS)
  }

  function scheduleReconnect(): void {
    if (stopped) return
    const delay = RECONNECT_DELAYS[Math.min(reconnectAttempt, RECONNECT_DELAYS.length - 1)]
    reconnectAttempt += 1
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      openSource()
    }, delay)
  }

  function openSource(): void {
    if (typeof window === 'undefined' || typeof EventSource === 'undefined') {
      startPolling()
      return
    }
    try {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      source = new EventSource(`${apiBase}/me/events`, { withCredentials: true })
    } catch {
      startPolling()
      return
    }

    source.addEventListener('open', () => {
      isConnected.value = true
      reconnectAttempt = 0
      clearPolling()
      try {
        useNotificationsStore().setStreamConnected(true)
      } catch {
        // store hors layout PME
      }
    })

    source.addEventListener('notification.created', (ev) => {
      const data = (ev as MessageEvent).data
      try {
        const payload = JSON.parse(data)
        useNotificationsStore().pushFromStream(payload)
      } catch {
        // payload invalide → ignoré
      }
    })

    // F52 — réception du bulk-read émis par /read-all (autres onglets).
    source.addEventListener('notification.bulk_read', (ev) => {
      const data = (ev as MessageEvent).data
      try {
        const payload = JSON.parse(data)
        useNotificationsStore().applyBulkReadFromStream(payload)
      } catch {
        // payload invalide → ignoré
      }
    })

    // F52 — réception du read individuel (autres onglets).
    source.addEventListener('notification.read', (ev) => {
      const data = (ev as MessageEvent).data
      try {
        const payload = JSON.parse(data) as { id?: string }
        if (typeof payload?.id === 'string') {
          const store = useNotificationsStore()
          const found = store.items.find((n) => n.id === payload.id)
          if (found && !found.read_at) {
            store.pushFromStream({ ...found, read_at: new Date().toISOString() })
          }
        }
      } catch {
        // payload invalide → ignoré
      }
    })

    source.addEventListener('error', () => {
      isConnected.value = false
      try {
        useNotificationsStore().setStreamConnected(false)
      } catch {
        // ignore
      }
      source?.close()
      source = null
      startPolling()
      scheduleReconnect()
    })
  }

  function start(): void {
    if (typeof window === 'undefined') return
    stopped = false
    if (source || reconnectTimer) return
    openSource()
  }

  function stop(): void {
    stopped = true
    clearReconnectTimer()
    clearPolling()
    if (source) {
      source.close()
      source = null
    }
    isConnected.value = false
    try {
      useNotificationsStore().setStreamConnected(false)
    } catch {
      // ignore
    }
  }

  instance = { start, stop, isConnected: readonly(isConnected) }
  return instance
}

// Test-only reset
export function __resetNotificationsStream(): void {
  instance = null
}
