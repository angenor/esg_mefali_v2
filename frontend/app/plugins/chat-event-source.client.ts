/**
 * chat-event-source.client — Plugin Nuxt client-only.
 *
 * Ouvre un EventSource sur /me/events (F18) et publie chaque frame typée dans
 * useChatEventBus. Filtre/normalise le champ `source` (le backend tague déjà
 * chaque mutation : `llm | manual | import | admin`).
 *
 * Référence : specs/041-chat-conversational-layer/research.md R3 ; F18.
 */
import { defineNuxtPlugin } from '#app'
import { useChatEventBus } from '~/composables/useChatEventBus'
import type { EventBusEvent, EventBusEventType, EventBusSource } from '~/types/chat'

interface RawEvent {
  event_type?: string
  entity_type?: string
  entity_id?: string
  fields_updated?: string[]
  source?: string
  ts?: string
}

const VALID_TYPES: EventBusEventType[] = [
  'entity_updated',
  'entity_created',
  'entity_deleted',
  'memory_updated',
]
const VALID_SOURCES: EventBusSource[] = ['llm', 'manual', 'import', 'admin']

function normalize(raw: RawEvent): EventBusEvent | null {
  const eventType = raw.event_type as EventBusEventType
  if (!VALID_TYPES.includes(eventType)) return null
  const source = (VALID_SOURCES as string[]).includes(raw.source ?? '')
    ? (raw.source as EventBusSource)
    : 'manual'
  return {
    eventType,
    entityType: String(raw.entity_type ?? ''),
    entityId: String(raw.entity_id ?? ''),
    fieldsUpdated: raw.fields_updated,
    source,
    ts: raw.ts ?? new Date().toISOString(),
  }
}

export default defineNuxtPlugin((nuxtApp) => {
  if (typeof window === 'undefined') return
  const cfg = nuxtApp.$config
  const apiBase = String(cfg.public?.apiBase ?? 'http://localhost:8010').replace(/\/$/, '')
  const url = `${apiBase}/me/events`
  let es: EventSource | null = null
  let retryAttempt = 0
  const BACKOFF = [1000, 2000, 4000, 8000, 8000]

  function open(): void {
    try {
      es = new EventSource(url, { withCredentials: true })
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[chat-event-source] EventSource init failed', err)
      return
    }
    const bus = useChatEventBus()

    const handle = (raw: MessageEvent): void => {
      let parsed: RawEvent | null = null
      try {
        parsed = JSON.parse(raw.data) as RawEvent
      } catch {
        return
      }
      if (!parsed) return
      const normalized = normalize(parsed)
      if (!normalized) return
      bus.emit(normalized.eventType, normalized)
    }

    for (const type of VALID_TYPES) {
      es.addEventListener(type, handle as EventListener)
    }
    es.onopen = (): void => {
      retryAttempt = 0
    }
    es.onerror = (): void => {
      es?.close()
      es = null
      const delay = BACKOFF[Math.min(retryAttempt, BACKOFF.length - 1)] ?? 8000
      retryAttempt += 1
      if (retryAttempt > 10) return
      setTimeout(open, delay)
    }
  }

  open()

  window.addEventListener('beforeunload', () => {
    es?.close()
    es = null
  })
})
