// F45 T016 — KPI réactif de progression.
import { computed, type ComputedRef } from "vue"
import { useActionPlanStore } from "~/stores/actionPlan"
import type { CompletionStats } from "~/types/actionPlan"

export function useActionPlanCompletion(): ComputedRef<CompletionStats> {
  const store = useActionPlanStore()
  return computed(() => store.completionStats)
}
