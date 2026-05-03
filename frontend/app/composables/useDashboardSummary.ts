// F44 T010 — Composable principal du dashboard PME.
//
// Cf. contracts/frontend-components.md C-CMP-1 et chat-eventbus-sync.md.
// - Fetch initial au mount.
// - Polling 60 s tant que l'onglet est focus (Page Visibility API).
// - Abonnement aux events dashboard via `useDashboardBus`, invalidation ciblée
//   par bloc (cf. EVENT_TO_BLOCK_MAP).
// - Garde-fou anti-loop : ignore les events `source: 'dashboard'` corrélés
//   par `id` pendant 5 s après émission locale.
import { computed, onBeforeUnmount, onMounted, type ComputedRef } from "vue"
import { useDashboardStore, type DashboardSummaryOut } from "~/stores/dashboard"
import {
  EVENT_TO_BLOCK_MAP,
  type BlockKey,
  type DashboardEventName,
} from "~/lib/dashboardEventMap"
import {
  useDashboardBus,
  type DashboardBusEvent,
} from "~/composables/useDashboardBus"
import { useT } from "~/composables/useT"
import {
  mapSummaryToCardViewModels,
  type DashboardCardViewModels,
} from "~/lib/mapSummaryToCardViewModels"

const POLL_INTERVAL_MS = 60_000
const LOCAL_MUTATION_TTL_MS = 5_000

export interface UseDashboardSummary {
  summary: ComputedRef<DashboardSummaryOut | null>
  loading: ComputedRef<boolean>
  errorByBlock: ComputedRef<Partial<Record<BlockKey | "*", string>>>
  vms: ComputedRef<DashboardCardViewModels>
  refresh: (blocks?: BlockKey[]) => Promise<void>
  /** Marque une mutation locale (id) pour anti-loop : les events `source: 'dashboard'` portant cet id seront ignorés pendant 5 s. */
  trackLocalMutation: (id: string) => void
}

export interface UseDashboardSummaryOptions {
  hasProjet?: boolean
}

export function useDashboardSummary(
  options: UseDashboardSummaryOptions = {},
): UseDashboardSummary {
  const store = useDashboardStore()
  const bus = useDashboardBus()
  const { t } = useT()

  let intervalId: ReturnType<typeof setInterval> | null = null
  const offHandlers: Array<() => void> = []
  const localMutations = new Map<string, number>()

  function pruneExpiredMutations(): void {
    const now = Date.now()
    for (const [id, ts] of localMutations.entries()) {
      if (now - ts > LOCAL_MUTATION_TTL_MS) localMutations.delete(id)
    }
  }

  function trackLocalMutation(id: string): void {
    localMutations.set(id, Date.now())
  }

  async function refresh(blocks?: BlockKey[]): Promise<void> {
    if (blocks && blocks.length > 0) {
      await store.fetchSummary({ scope: blocks })
    } else {
      await store.fetchSummary()
    }
  }

  function startPolling(): void {
    if (intervalId !== null) return
    intervalId = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState === "hidden") return
      void refresh()
    }, POLL_INTERVAL_MS)
  }

  function stopPolling(): void {
    if (intervalId !== null) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  function onVisibilityChange(): void {
    if (typeof document === "undefined") return
    if (document.visibilityState === "visible") {
      void refresh()
      startPolling()
    } else {
      stopPolling()
    }
  }

  function makeHandler(eventName: DashboardEventName) {
    return (event: DashboardBusEvent) => {
      pruneExpiredMutations()
      // Anti-loop : event d'origine locale corrélé à une mutation tracée.
      if (event.source === "dashboard" && event.id && localMutations.has(event.id)) {
        return
      }
      const blocks = EVENT_TO_BLOCK_MAP[eventName]
      if (!blocks || blocks.length === 0) return
      for (const block of blocks) store.invalidate(block)
      void refresh([...blocks])
    }
  }

  onMounted(() => {
    void refresh()
    startPolling()
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", onVisibilityChange)
    }
    for (const eventName of Object.keys(EVENT_TO_BLOCK_MAP) as DashboardEventName[]) {
      const handler = makeHandler(eventName)
      const off = bus.on(eventName, handler)
      offHandlers.push(off)
    }
  })

  onBeforeUnmount(() => {
    stopPolling()
    if (typeof document !== "undefined") {
      document.removeEventListener("visibilitychange", onVisibilityChange)
    }
    for (const off of offHandlers) off()
    offHandlers.length = 0
    localMutations.clear()
  })

  const vms = computed<DashboardCardViewModels>(() =>
    mapSummaryToCardViewModels(store.summary, {
      t,
      hasProjet: options.hasProjet ?? false,
      isLoading: store.loading && store.summary === null,
      blockErrors: store.blockErrors,
      onRetry: (block: BlockKey) => {
        void refresh([block])
      },
    }),
  )

  return {
    summary: computed(() => store.summary),
    loading: computed(() => store.loading),
    errorByBlock: computed(() => store.blockErrors),
    vms,
    refresh,
    trackLocalMutation,
  }
}
