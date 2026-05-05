// F44 — Bus mémoire dédié au dashboard PME (in-tab JS).
//
// Nous gardons un singleton mitt distinct de `useChatEventBus` pour ne pas
// polluer son typage (entity_*) avec les events spécifiques au dashboard
// (`scoring:computed`, etc.). Cf. specs/044-dashboard-pme-ui/contracts/chat-eventbus-sync.md.
import mitt, { type Emitter } from "mitt"
import type { DashboardEventName } from "~/lib/dashboardEventMap"

export interface DashboardBusEvent {
  /** Identifiant de l'entité touchée (UUID, optionnel selon l'event). */
  id?: string
  /** Origine de l'event — utilisée pour anti-loop côté `useDashboardSummary`. */
  source?: "dashboard" | "chat" | "backend" | "llm"
  /** Payload libre selon l'event. */
  data?: Record<string, unknown>
}

type DashboardEvents = Record<DashboardEventName, DashboardBusEvent>

let singleton: Emitter<DashboardEvents> | null = null

function getEmitter(): Emitter<DashboardEvents> {
  if (!singleton) singleton = mitt<DashboardEvents>()
  return singleton
}

// Registre global anti-loop : ids des mutations locales à ignorer pendant TTL (5 s).
const LOCAL_MUTATION_TTL_MS = 5_000
const localMutationIds = new Map<string, number>()

export function trackLocalMutation(id: string): void {
  localMutationIds.set(id, Date.now())
}

export function isLocalMutation(id: string): boolean {
  const ts = localMutationIds.get(id)
  if (ts === undefined) return false
  if (Date.now() - ts > LOCAL_MUTATION_TTL_MS) {
    localMutationIds.delete(id)
    return false
  }
  return true
}

export interface UseDashboardBus {
  on<K extends DashboardEventName>(
    type: K,
    handler: (event: DashboardBusEvent) => void,
  ): () => void
  off<K extends DashboardEventName>(
    type: K,
    handler: (event: DashboardBusEvent) => void,
  ): void
  emit<K extends DashboardEventName>(type: K, event: DashboardBusEvent): void
}

export function useDashboardBus(): UseDashboardBus {
  const emitter = getEmitter()
  return {
    on(type, handler) {
      emitter.on(type, handler)
      return () => emitter.off(type, handler)
    },
    off(type, handler) {
      emitter.off(type, handler)
    },
    emit(type, event) {
      emitter.emit(type, event)
    },
  }
}

export function __resetDashboardBus(): void {
  singleton = null
  localMutationIds.clear()
}
