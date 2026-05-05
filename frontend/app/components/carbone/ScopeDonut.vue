<script setup lang="ts">
// F47 T035 [US1] — Donut Scope 1/2/3 (wrap VizDonutChart F40).
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-components.md §ScopeDonut.

import { computed } from "vue"
import Decimal from "decimal.js"
import VizDonutChart from "~/components/viz/VizDonutChart.vue"
import { useT } from "~/composables/useT"
import type { Scope } from "~/types/carbon"
import type { PieSeries } from "~/types/viz/chart"

interface Props {
  byScope: Record<Scope, string> | null | undefined
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })

const { t } = useT()

const series = computed<PieSeries>(() => {
  const labels = [
    t("carbon.scopes.short.1"),
    t("carbon.scopes.short.2"),
    t("carbon.scopes.short.3"),
  ]
  const map = props.byScope ?? { "1": "0", "2": "0", "3": "0" }
  // Conversion kgCO2e -> tCO2e pour homogénéité avec le KPI
  const data = (["1", "2", "3"] as Scope[]).map((s) =>
    new Decimal(map[s] ?? "0").dividedBy(1000).toNumber(),
  )
  return { labels, data }
})

const isEmpty = computed(() =>
  series.value.data.every((v) => v === 0),
)

const longDescription = computed(() => {
  const map = props.byScope ?? { "1": "0", "2": "0", "3": "0" }
  const lines = (["1", "2", "3"] as Scope[]).map((s) => {
    const t = new Decimal(map[s] ?? "0").dividedBy(1000).toFixed(2)
    return `${t} tCO₂e Scope ${s}`
  })
  return `Répartition par scope : ${lines.join(", ")}`
})
</script>

<template>
  <div class="rounded-2xl bg-white p-6 shadow-sm border border-neutral-200">
    <h3 class="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
      Répartition Scope 1 / 2 / 3
    </h3>
    <VizDonutChart
      :series="series"
      :loading="loading"
      :empty="isEmpty"
      size="md"
      :aria-label="`Répartition d'empreinte carbone par scope (Scope 1, Scope 2, Scope 3)`"
      :long-description="longDescription"
    />
  </div>
</template>
