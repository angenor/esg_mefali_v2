<script setup lang="ts">
// F51 T086 — 3 charts (bar/line/donut) du simulateur.
import { computed } from "vue"
import { useSimulateurStore } from "~/stores/simulateur"
import { formatMoney } from "~/utils/moneyFormat"
import VizLineChart from "~/components/viz/VizLineChart.vue"
import VizDonutChart from "~/components/viz/VizDonutChart.vue"

const store = useSimulateurStore()
const results = computed(() => store.results)

const decompositionSeries = computed(() => {
  const d = results.value?.decomposition_pct
  if (!d) return null
  return {
    labels: ["Principal", "Intérêts", "Subvention"],
    data: [d.principal, d.interets, d.subvention],
  }
})

const mensualitesSeries = computed(() => {
  const m = results.value?.mensualites ?? []
  return [
    {
      label: "Mensualité",
      points: m.slice(0, 60).map((p) => ({
        x: p.mois,
        y: Number(p.amount),
      })),
    },
  ]
})

const computingClass = computed(() =>
  store.computing ? "opacity-70 transition-opacity" : "transition-opacity",
)
</script>

<template>
  <div class="space-y-6">
    <div v-if="!results && !store.computing" class="rounded border border-dashed border-gray-300 p-8 text-center text-gray-500">
      Ajustez les sliders pour lancer le calcul.
    </div>

    <div v-else-if="!results" class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div v-for="i in 3" :key="i" class="h-40 animate-pulse rounded bg-gray-100" />
    </div>

    <div v-else :class="computingClass">
      <div class="grid gap-4 md:grid-cols-3">
        <article class="rounded-lg border border-gray-200 bg-white p-4">
          <h3 class="text-sm font-semibold text-gray-600">Coût total</h3>
          <p class="mt-2 text-2xl font-bold text-emerald-700">
            {{ formatMoney(results.cout_total) }}
          </p>
        </article>
        <article class="rounded-lg border border-gray-200 bg-white p-4">
          <h3 class="text-sm font-semibold text-gray-600">Économie estimée</h3>
          <p class="mt-2 text-2xl font-bold text-blue-700">
            {{ formatMoney(results.economie_estimee) }}
          </p>
        </article>
        <article class="rounded-lg border border-gray-200 bg-white p-4">
          <h3 class="text-sm font-semibold text-gray-600">CO₂ évité</h3>
          <p class="mt-2 text-2xl font-bold text-amber-700">
            {{ results.co2_evite_t }} t
          </p>
        </article>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <article class="rounded-lg border border-gray-200 bg-white p-4">
          <h3 class="mb-2 font-semibold">Répartition du financement</h3>
          <VizDonutChart
            v-if="decompositionSeries"
            :series="decompositionSeries"
            title="Décomposition"
          />
        </article>
        <article class="rounded-lg border border-gray-200 bg-white p-4">
          <h3 class="mb-2 font-semibold">Mensualités (5 ans max)</h3>
          <VizLineChart :series="mensualitesSeries" title="Mensualités" />
        </article>
      </div>
    </div>
  </div>
</template>
