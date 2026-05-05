/**
 * F48 US7 — Composable useCreditHistory.
 *
 * Lit l'historique depuis le store useCreditScoreStore (cache 60 s).
 * Dérive `current`, `previous`, `delta` côté composable.
 * Abonnement EventBus `entity_updated{credit_score}` → invalidation ciblée.
 */

import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useCreditScoreStore } from '~/stores/creditScore'
import { useChatEventBus } from '~/composables/useChatEventBus'
import type { HistoryEntry } from '~/types/creditScore'
import type { EventBusEvent } from '~/types/chat'

interface UseCreditHistoryOptions {
  limit?: number
}

export function useCreditHistory(options: UseCreditHistoryOptions = {}) {
  const limit = options.limit ?? 6
  const store = useCreditScoreStore()
  const bus = useChatEventBus()

  const entries = computed<HistoryEntry[]>(() => store.history)
  const current = computed<HistoryEntry | null>(() => store.history[0] ?? null)
  const previous = computed<HistoryEntry | null>(() => store.history[1] ?? null)
  const delta = computed<number | null>(() => {
    const c = current.value
    const p = previous.value
    if (!c || !p) return null
    return c.combine - p.combine
  })
  const loading = computed<boolean>(() => store.loading.history)
  const error = computed<string | null>(() => store.error.history)

  async function refresh(opts: { force?: boolean } = {}) {
    await store.refreshHistory({ limit, ...opts })
  }

  const handler = (event: EventBusEvent) => {
    if (event.entityType === 'credit_score' || event.entityType === 'credit_data') {
      store.invalidateHistory()
      void store.refreshHistory({ limit, force: true })
    }
  }

  let off: (() => void) | null = null
  onMounted(() => {
    off = bus.on('entity_updated', handler)
    void store.refreshHistory({ limit })
  })
  onBeforeUnmount(() => {
    if (off) off()
  })

  return { entries, current, previous, delta, loading, error, refresh }
}
