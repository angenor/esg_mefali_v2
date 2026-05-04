<script setup lang="ts">
// F47 T062 [US4] — Courbe d'évolution annuelle (total + 3 scopes), max 5 ans.
//
// Wrap <VizLineChart>. Légende interactive : toggle scope masque la série,
// le total reste affiché. Tableau sr-only pour a11y.

import { computed, ref } from "vue"
import VizLineChart from "~/components/viz/VizLineChart.vue"
import VizEmptyState from "~/components/viz/VizEmptyState.vue"
import { useCarbonHistory } from "~/composables/useCarbonHistory"
import { useCarbonStore } from "~/stores/carbon"
import { useT } from "~/composables/useT"
import type { ChartSeries } from "~/types/viz/chart"

const { t } = useT()
const history = useCarbonHistory()
const store = useCarbonStore()

const HIDDEN_KEYS = new Set<string>()
const hiddenVersion = ref(0)

function toggle(key: string): void {
  if (HIDDEN_KEYS.has(key)) HIDDEN_KEYS.delete(key)
  else HIDDEN_KEYS.add(key)
  hiddenVersion.value += 1
}

const chartSeries = computed<ChartSeries[]>(() => {
  void hiddenVersion.value
  return history.series.value
    .filter((s) => !HIDDEN_KEYS.has(s.key))
    .map((s) => ({
      label: s.label,
      points: s.points
        .filter((p) => p.value !== null)
        .map((p) => ({ x: String(p.year), y: p.value as number })),
    }))
})

const isEmpty = computed(() => chartSeries.value.every((s) => s.points.length === 0))
const currentYear = computed(() => store.selectedYear)
</script>

<template>
  <section
    class="rounded-2xl bg-white p-6 shadow-sm border border-neutral-200"
    :aria-label="t('carbon.kpis.deltaVsLastYear')"
  >
    <header class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-semibold text-neutral-700">
        {{ t("carbon.scopes.short.1") }} · {{ t("carbon.scopes.short.2") }} ·
        {{ t("carbon.scopes.short.3") }}
      </h3>
    </header>

    <VizEmptyState v-if="isEmpty" />
    <VizLineChart
      v-else
      :series="chartSeries"
      :loading="history.loading.value"
      :aria-label="t('carbon.kpis.deltaVsLastYear')"
      size="md"
    />

    <ul class="mt-3 flex flex-wrap gap-2" aria-label="Légende">
      <li v-for="s in history.series.value" :key="s.key">
        <button
          type="button"
          class="text-xs px-2 py-1 rounded-full border transition-colors"
          :class="
            HIDDEN_KEYS.has(s.key)
              ? 'border-neutral-200 text-neutral-400 line-through'
              : 'border-neutral-300 text-neutral-700 hover:bg-neutral-50'
          "
          :aria-pressed="!HIDDEN_KEYS.has(s.key)"
          @click="toggle(s.key)"
        >
          {{ s.label }}
        </button>
      </li>
    </ul>

    <table class="sr-only">
      <caption>Évolution annuelle de l'empreinte carbone (tCO₂e)</caption>
      <thead>
        <tr>
          <th>Année</th>
          <th v-for="s in history.series.value" :key="s.key">{{ s.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(_, idx) in history.series.value[0]?.points ?? []"
          :key="idx"
        >
          <th scope="row">
            {{ history.series.value[0]?.points[idx]?.year }}
            <span v-if="history.series.value[0]?.points[idx]?.year === currentYear">
              (année courante)</span>
          </th>
          <td v-for="s in history.series.value" :key="s.key">
            {{ s.points[idx]?.value ?? "—" }}
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
