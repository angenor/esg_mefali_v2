// F46 T040 [US2] — Composable pour la sélection de référentiels à comparer.
//
// Cf. specs/046-scoring-esg-ui/data-model.md §4.3.

import { computed, ref, watch, type ComputedRef, type Ref } from "vue"
import { useScoringStore } from "~/stores/scoring"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"
import type {
  CompareDatasetVM,
  CompareSeriesVM,
  PillarCode,
} from "~/types/scoring"

export const SCORING_COMPARE_MAX = 5

export interface UseScoringCompareApi {
  selectedRefs: Ref<string[]>
  dataset: ComputedRef<CompareDatasetVM>
  select(code: string): void
  unselect(code: string): void
  toggle(code: string): void
  clear(): void
}

export function useScoringCompare(): UseScoringCompareApi {
  const store = useScoringStore()
  const toast = useToast()
  const { t } = useT()

  const initial = store.currentReferentielCode
    ? [store.currentReferentielCode]
    : []
  const selectedRefs = ref<string[]>([...initial])

  // Si aucun référentiel courant au mount, synchroniser quand il devient disponible.
  watch(
    () => store.currentReferentielCode,
    (code) => {
      if (code && selectedRefs.value.length === 0) {
        selectedRefs.value = [code]
      }
    },
  )

  function select(code: string): void {
    if (selectedRefs.value.includes(code)) return
    if (selectedRefs.value.length >= SCORING_COMPARE_MAX) {
      toast.push({
        severity: "warning",
        message: t("scoring.errors.tooManyCompared"),
        duration: 4000,
      })
      return
    }
    selectedRefs.value = [...selectedRefs.value, code]
  }

  function unselect(code: string): void {
    selectedRefs.value = selectedRefs.value.filter((c) => c !== code)
  }

  function toggle(code: string): void {
    if (selectedRefs.value.includes(code)) {
      unselect(code)
    } else {
      select(code)
    }
  }

  function clear(): void {
    selectedRefs.value = []
  }

  const dataset = computed<CompareDatasetVM>(() => {
    const series: CompareSeriesVM[] = []
    const pillars: PillarCode[] = []
    const seen = new Set<PillarCode>()
    for (const code of selectedRefs.value) {
      const sum = store.summariesByRef[code]
      if (!sum) continue
      series.push({
        referentielCode: sum.referentielCode,
        referentielVersion: sum.referentielVersion,
        scoreGlobal: sum.scoreGlobal,
        scoresByPillar: sum.scoresByPillar,
      })
      for (const p of Object.keys(sum.scoresByPillar)) {
        if (!seen.has(p)) {
          seen.add(p)
          pillars.push(p)
        }
      }
    }
    return { referentiels: series, pillars }
  })

  return { selectedRefs, dataset, select, unselect, toggle, clear }
}
