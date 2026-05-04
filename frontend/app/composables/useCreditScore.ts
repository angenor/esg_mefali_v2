/**
 * F48 — Composable useCreditScore : orchestre store + EventBus chat.
 *
 * Cf. specs/048-credit-scoring-ui/contracts/chat-eventbus-sync.md.
 */

import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useCreditScoreStore } from '~/stores/creditScore'
import { useChatEventBus } from '~/composables/useChatEventBus'
import type { EventBusEvent } from '~/types/chat'

const DEBOUNCE_MS = 200
const ECHO_GUARD_MS = 500

export function useCreditScore() {
  const store = useCreditScoreStore()
  const bus = useChatEventBus()
  const lastLocalEmissionAt = ref<number>(0)

  const score = computed(() => store.score)
  const subscores = computed(() => store.score?.subscores ?? null)
  const classification = computed(() => store.score?.classification ?? null)
  const partialCoverage = computed(() => store.score?.partialCoverage ?? false)
  const loading = computed(() => store.loading.score)
  const error = computed(() => store.error.score)

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  const scheduleRefresh = () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      void store.refreshScore()
      void store.refreshHistory({ force: true })
    }, DEBOUNCE_MS)
  }

  const handler = (event: EventBusEvent) => {
    if (
      event.entityType !== 'credit_score'
      && event.entityType !== 'credit_data'
    ) {
      return
    }
    if (
      event.source === 'manual'
      && Date.now() - lastLocalEmissionAt.value < ECHO_GUARD_MS
    ) {
      return
    }
    scheduleRefresh()
  }

  let off: (() => void) | null = null

  onMounted(async () => {
    off = bus.on('entity_updated', handler)
    await Promise.all([
      store.refreshScore(),
      store.refreshHistory({ force: true }),
    ])
  })

  onBeforeUnmount(() => {
    if (off) off()
    if (debounceTimer) clearTimeout(debounceTimer)
  })

  const refresh = async () => {
    await store.refreshAll()
  }

  const markLocalEmission = () => {
    lastLocalEmissionAt.value = Date.now()
  }

  return {
    score,
    subscores,
    classification,
    partialCoverage,
    loading,
    error,
    refresh,
    markLocalEmission,
  }
}
