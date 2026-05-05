// F49 T017 — Composable d'écoute du flux SSE de génération.
//
// Cas réels rencontrés :
// 1. Backend asynchrone (cible) : EventSource sur /me/rapports/generate/{id}/stream.
// 2. Backend synchrone (état actuel F24) : `useReportsStore().generate()`
//    transitionne directement vers `ready` avant que le composable ne soit
//    appelé ; le composable est alors un no-op.
//
// Le composable s'auto-ferme sur `done`/`failed` et reconnecte avec
// `Last-Event-ID` (header HTTP) pour la reprise après déconnexion.

import { ref, onScopeDispose } from "vue"
import { useReportsStore } from "~/stores/reports"
import { reportsApi } from "~/services/api/reports"

interface StreamHandle {
  close(): void
  isOpen: () => boolean
}

interface StreamPayload {
  step?: string
  percent?: number
  rapport_id?: string
  download_filename?: string
  error?: string
}

export function useReportGenerationStream(generationId: string): StreamHandle {
  const store = useReportsStore()
  const open = ref(false)
  let es: EventSource | null = null

  function start() {
    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      // SSR ou navigateur sans support : fallback no-op (le store gère
      // déjà la transition `ready` quand le backend est synchrone).
      return
    }
    // Le backend MVP ne supporte pas Last-Event-ID via querystring ; on
    // s'en remet au comportement natif d'EventSource (header automatique
    // sur reconnexion).
    const url = reportsApi.buildStreamUrl(generationId)
    try {
      es = new EventSource(url, { withCredentials: true })
    } catch {
      es = null
      return
    }
    open.value = true

    es.addEventListener("progress", (ev) => {
      const data = parseEvent(ev)
      const eventId = (ev as MessageEvent).lastEventId
        ? Number((ev as MessageEvent).lastEventId)
        : undefined
      store.applyStreamEvent(generationId, "progress", { ...data, eventId })
    })
    es.addEventListener("done", (ev) => {
      const data = parseEvent(ev)
      const eventId = (ev as MessageEvent).lastEventId
        ? Number((ev as MessageEvent).lastEventId)
        : undefined
      store.applyStreamEvent(generationId, "done", { ...data, eventId })
      close()
    })
    es.addEventListener("failed", (ev) => {
      const data = parseEvent(ev)
      const eventId = (ev as MessageEvent).lastEventId
        ? Number((ev as MessageEvent).lastEventId)
        : undefined
      store.applyStreamEvent(generationId, "failed", { ...data, eventId })
      close()
    })
    es.onerror = () => {
      // EventSource reconnecte automatiquement. Si la connexion se ferme
      // définitivement (4xx), on bascule en `failed`.
      if (es && es.readyState === EventSource.CLOSED) {
        store.applyStreamEvent(generationId, "failed", {
          error: "stream_unavailable",
        })
        close()
      }
    }
  }

  function close() {
    if (es) {
      es.close()
      es = null
    }
    open.value = false
  }

  function parseEvent(ev: Event): StreamPayload {
    try {
      const me = ev as MessageEvent
      return JSON.parse(me.data ?? "{}") as StreamPayload
    } catch {
      return {}
    }
  }

  start()
  onScopeDispose(close)

  return {
    close,
    isOpen: () => open.value,
  }
}
