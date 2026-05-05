<script setup lang="ts">
// F47 T034 [US1] — Vue synthèse : KPI total tCO2e + delta vs N-1 + couverture %.
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-components.md §CarbonOverview.

import { computed } from "vue"
import Decimal from "decimal.js"
import UiSkeleton from "~/components/ui/UiSkeleton.vue"
import UiProgress from "~/components/ui/UiProgress.vue"
import { useT } from "~/composables/useT"
import type { CarbonFootprint } from "~/types/carbon"
import type { CoverageSnapshot } from "~/lib/computeCarbonCoverage"

interface Props {
  footprint: CarbonFootprint | null
  previousYearFootprint: CarbonFootprint | null
  coverage: CoverageSnapshot | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })

const { t } = useT()

const totalFormatted = computed(() => {
  if (!props.footprint) return "—"
  // tabular-nums : 2 décimales fixes via Decimal
  return new Decimal(props.footprint.total_tco2e).toFixed(2)
})

interface DeltaInfo {
  value: string
  sign: "positive" | "negative" | "neutral"
}

const delta = computed<DeltaInfo>(() => {
  if (!props.footprint || !props.previousYearFootprint) {
    return { value: "—", sign: "neutral" }
  }
  const cur = new Decimal(props.footprint.total_tco2e)
  const prev = new Decimal(props.previousYearFootprint.total_tco2e)
  if (prev.isZero()) {
    return { value: "—", sign: "neutral" }
  }
  const diff = cur.minus(prev).dividedBy(prev).times(100)
  const sign = diff.gt(0) ? "positive" : diff.lt(0) ? "negative" : "neutral"
  const formatted = `${diff.gt(0) ? "+" : ""}${diff.toFixed(1)} %`
  return { value: formatted, sign }
})

const coveragePct = computed(() =>
  props.coverage ? props.coverage.globalPct : 0,
)
</script>

<template>
  <section
    class="rounded-2xl bg-white p-6 shadow-sm border border-neutral-200"
    :aria-label="t('carbon.kpis.total')"
  >
    <UiSkeleton v-if="loading" class="h-32" />
    <div v-else class="grid gap-4">
      <!-- KPI total -->
      <div>
        <div class="text-sm uppercase tracking-wide text-neutral-500">
          {{ t("carbon.kpis.total") }}
        </div>
        <div class="mt-1 flex items-baseline gap-2">
          <span class="text-4xl font-semibold text-neutral-900 tabular-nums">
            {{ totalFormatted }}
          </span>
          <span class="text-lg text-neutral-600">
            {{ t("carbon.kpis.totalUnit") }}
          </span>
        </div>
      </div>

      <!-- Delta vs N-1 -->
      <div>
        <div class="text-xs uppercase tracking-wide text-neutral-500">
          {{ t("carbon.kpis.deltaVsLastYear") }}
        </div>
        <div
          class="mt-1 text-lg font-medium tabular-nums"
          :class="{
            'text-emerald-600': delta.sign === 'negative',
            'text-rose-600': delta.sign === 'positive',
            'text-neutral-500': delta.sign === 'neutral',
          }"
        >
          {{ delta.value }}
          <span
            v-if="delta.sign === 'neutral'"
            class="ml-2 text-sm text-neutral-400"
          >
            {{ t("carbon.kpis.noComparison") }}
          </span>
        </div>
      </div>

      <!-- Couverture -->
      <div>
        <div class="text-xs uppercase tracking-wide text-neutral-500">
          {{ t("carbon.kpis.coverage") }}
        </div>
        <div class="mt-1 flex items-center gap-3">
          <UiProgress :model-value="coveragePct" class="flex-1" />
          <span class="text-sm font-medium text-neutral-700 tabular-nums">
            {{ Math.round(coveragePct) }} %
          </span>
        </div>
      </div>
    </div>
  </section>
</template>
