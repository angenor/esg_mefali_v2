// F46 T050 [US3] — Composable useScoringHistory(refCode).
//
// Expose entries/loading/error pour le drawer indicateur et le HistoryChart (US7).
// Cf. specs/046-scoring-esg-ui/data-model.md §4.2.

import { computed, ref, type ComputedRef, type Ref } from "vue"
import { useScoringStore } from "~/stores/scoring"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"
import type { ScoreHistoryEntryVM } from "~/types/scoring"

export interface UseScoringHistoryApi {
  entries: ComputedRef<ScoreHistoryEntryVM[]>
  loading: Ref<boolean>
  error: Ref<string | null>
  load(force?: boolean): Promise<void>
}

export function useScoringHistory(
  refCode: string,
  limit = 12,
): UseScoringHistoryApi {
  const store = useScoringStore()
  const toast = useToast()
  const { t } = useT()

  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)

  const entries = computed<ScoreHistoryEntryVM[]>(() => {
    const list = store.historyByRef[refCode] ?? []
    return [...list].sort((a, b) => b.computedAt.localeCompare(a.computedAt))
  })

  async function load(force = false): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await store.loadHistory(refCode, limit, force)
      // Si le store a stocké une erreur, surface en toast.
      const stored = store.errorByRef[refCode]
      if (stored && !store.historyByRef[refCode]) {
        error.value = stored
        toast.push({
          severity: "warning",
          message: t("scoring.empty.noHistory"),
          duration: 4000,
        })
      }
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "history_failed"
      toast.push({
        severity: "warning",
        message: t("scoring.empty.noHistory"),
        duration: 4000,
      })
    } finally {
      loading.value = false
    }
  }

  return { entries, loading, error, load }
}
