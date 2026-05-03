/**
 * useChatEventBus — bus client P8 (sync bidirectionnelle profil ↔ chat).
 *
 * Référence : specs/041-chat-conversational-layer/research.md R3.
 * mitt minimaliste, anti-loop par filtrage `source === 'llm'` au niveau des
 * listeners qui re-déclencheraient l'orchestrateur LLM.
 */
import mitt, { type Emitter } from 'mitt'
import type { EventBusEvent } from '~/types/chat'

type Events = {
  entity_updated: EventBusEvent
  entity_created: EventBusEvent
  entity_deleted: EventBusEvent
  memory_updated: EventBusEvent
}

let singleton: Emitter<Events> | null = null

function getEmitter(): Emitter<Events> {
  if (!singleton) singleton = mitt<Events>()
  return singleton
}

export type ListenerOptions = {
  /** Si vrai, le listener est ignoré pour les events `source === 'llm'` (anti-loop). */
  ignoreLlmSource?: boolean
}

export interface UseChatEventBus {
  on<K extends keyof Events>(
    type: K,
    handler: (event: Events[K]) => void,
    options?: ListenerOptions,
  ): () => void
  off<K extends keyof Events>(type: K, handler: (event: Events[K]) => void): void
  emit<K extends keyof Events>(type: K, event: Events[K]): void
}

export function useChatEventBus(): UseChatEventBus {
  const emitter = getEmitter()
  return {
    on(type, handler, options = {}) {
      const wrapped: typeof handler = (event) => {
        if (options.ignoreLlmSource && event.source === 'llm') return
        handler(event)
      }
      emitter.on(type, wrapped)
      return () => emitter.off(type, wrapped)
    },
    off(type, handler) {
      emitter.off(type, handler)
    },
    emit(type, event) {
      emitter.emit(type, event)
    },
  }
}

/** Reset le bus (tests uniquement). */
export function __resetChatEventBus(): void {
  singleton = null
}
