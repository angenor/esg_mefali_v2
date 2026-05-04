/**
 * F48 US3 — Composable useCreditEligibility.
 *
 * Lit les badges depuis le store useCreditScoreStore (cache 60 s).
 * Abonnement EventBus `entity_updated{credit_score}` → invalidation ciblée.
 */

import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useCreditScoreStore } from '~/stores/creditScore'
import { useChatEventBus } from '~/composables/useChatEventBus'
import type { EligibilityBadgeView } from '~/types/creditScore'
import type { EventBusEvent } from '~/types/chat'

export function useCreditEligibility() {
  const store = useCreditScoreStore()
  const bus = useChatEventBus()

  const items = computed<EligibilityBadgeView[]>(() => store.eligibility)
  const loading = computed<boolean>(() => store.loading.eligibility)
  const error = computed<string | null>(() => store.error.eligibility)
  const evaluatedAt = computed<number | null>(() => store.eligibilityLoadedAt)

  function byCode(code: string): EligibilityBadgeView | undefined {
    return store.eligibility.find((b) => b.code === code)
  }

  async function refresh(opts: { force?: boolean } = {}) {
    await store.refreshEligibility(opts)
  }

  const handler = (event: EventBusEvent) => {
    if (event.entityType === 'credit_score' || event.entityType === 'credit_data') {
      store.invalidateEligibility()
      void store.refreshEligibility({ force: true })
    }
  }

  let off: (() => void) | null = null

  onMounted(() => {
    off = bus.on('entity_updated', handler)
    void store.refreshEligibility()
  })

  onBeforeUnmount(() => {
    if (off) off()
  })

  return { items, loading, error, evaluatedAt, refresh, byCode }
}
