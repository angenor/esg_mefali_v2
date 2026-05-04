// F46 T018 — Composable principal /scoring : orchestre le store + bus chat.
//
// Cf. specs/046-scoring-esg-ui/data-model.md §4.1 et
// specs/046-scoring-esg-ui/contracts/chat-eventbus-sync.md.

import {
  computed,
  onBeforeUnmount,
  onMounted,
  type ComputedRef,
} from "vue"
import { useScoringStore } from "~/stores/scoring"
import { useChatEventBus } from "~/composables/useChatEventBus"
import type { EventBusEvent } from "~/types/chat"
import type {
  PillarBucketVM,
  ScoreDetailVM,
  ScoreSummaryVM,
} from "~/types/scoring"
import type { EntityType } from "~/services/api/scoring"

export const SCORING_DEBOUNCE_MS = 200

export interface UseScoringApi {
  currentSummary: ComputedRef<ScoreSummaryVM | null>
  currentDetail: ComputedRef<ScoreDetailVM | null>
  pillarsBuckets: ComputedRef<PillarBucketVM[]>
  coveragePercent: ComputedRef<number>
  loading: ComputedRef<boolean>
  error: ComputedRef<string | null>
  isSnapshot: ComputedRef<boolean>
  setCurrentReferentiel(code: string): Promise<void>
  recompute(refCode: string): Promise<void>
}

export function useScoring(
  entityType: EntityType,
  entityId: string,
): UseScoringApi {
  const store = useScoringStore()
  const bus = useChatEventBus()

  let unsubscribe: (() => void) | null = null
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let pendingPayloads: Array<Parameters<typeof store.onChatEntityUpdated>[0]> = []

  function flushPending(): void {
    const payloads = pendingPayloads
    pendingPayloads = []
    debounceTimer = null
    // dédupe : pour un même refCode courant, le store invalide les caches une fois.
    for (const p of payloads) {
      store.onChatEntityUpdated(p)
    }
  }

  function schedule(payload: Parameters<typeof store.onChatEntityUpdated>[0]): void {
    pendingPayloads.push(payload)
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(flushPending, SCORING_DEBOUNCE_MS)
  }

  const handler = (event: EventBusEvent): void => {
    if (event.eventType !== "entity_updated") return
    const allowed = new Set([
      "indicateur",
      "score_calculation",
      "entreprise",
      "projet",
    ])
    if (!allowed.has(event.entityType)) return
    schedule({
      entityType: event.entityType as
        | "indicateur"
        | "score_calculation"
        | "entreprise"
        | "projet",
      entityId: event.entityId,
      source: event.source,
      // EventBusEvent n'a pas meta — on lit fieldsUpdated pour 'entreprise'.
      meta:
        event.entityType === "entreprise" && event.fieldsUpdated?.length
          ? { field: event.fieldsUpdated[0] }
          : undefined,
    })
  }

  onMounted(() => {
    store.setEntity(entityType, entityId)
    void store.loadSummaries().catch(() => {
      /* error stored on store */
    })
    unsubscribe = bus.on("entity_updated", handler, { ignoreLlmSource: false })
  })

  onBeforeUnmount(() => {
    unsubscribe?.()
    unsubscribe = null
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    pendingPayloads = []
  })

  return {
    currentSummary: computed(() => store.currentSummary),
    currentDetail: computed(() => store.currentDetail),
    pillarsBuckets: computed(() => store.pillarsBuckets),
    coveragePercent: computed(() => store.coveragePercent),
    loading: computed(() => store.isLoading),
    error: computed(() => {
      const code = store.currentReferentielCode
      if (!code) return null
      return store.errorByRef[code] ?? null
    }),
    isSnapshot: computed(() => store.isSnapshot),
    setCurrentReferentiel: (code: string) => store.setCurrentReferentiel(code),
    recompute: (refCode: string) => store.recompute(refCode),
  }
}
