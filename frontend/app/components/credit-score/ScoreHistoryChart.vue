<!--
  F48 US7 — ScoreHistoryChart
  Courbe linéaire des N derniers calculs (ordre chronologique).
  Hover : date, valeur, version méthodologie.
  Si 1 seule entrée → message « Premier calcul ».
-->
<script setup lang="ts">
import { computed } from 'vue'
import VizLineChart from '~/components/viz/VizLineChart.vue'
import { useT } from '~/composables/useT'
import type { ChartSeries } from '~/types/viz/chart'
import type { HistoryEntry } from '~/types/creditScore'

interface Props {
  entries: HistoryEntry[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })
const { t } = useT()

const orderedEntries = computed<HistoryEntry[]>(() =>
  [...props.entries].sort((a, b) => a.computedAt.getTime() - b.computedAt.getTime()),
)

const series = computed<ChartSeries[]>(() => [
  {
    label: t('credit_score.history.series_label'),
    points: orderedEntries.value.map((e) => ({
      x: new Intl.DateTimeFormat('fr-FR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }).format(e.computedAt),
      y: e.combine,
    })),
  },
])

const longDescription = computed<string>(() => {
  if (orderedEntries.value.length === 0) return ''
  const parts = orderedEntries.value.map((e) => {
    const d = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' }).format(e.computedAt)
    return `${d} : ${e.combine}/100 (méthodologie v${e.methodologieVersion})`
  })
  return parts.join('. ')
})
</script>

<template>
  <section
    class="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200"
    aria-labelledby="history-title"
  >
    <header class="mb-3 flex items-baseline justify-between gap-2">
      <h2
        id="history-title"
        class="text-base font-semibold text-slate-900"
      >
        {{ t('credit_score.history.section_title') }}
      </h2>
      <p class="text-xs text-slate-500">
        {{ t('credit_score.history.section_hint') }}
      </p>
    </header>

    <div
      v-if="loading && entries.length === 0"
      class="rounded-md bg-slate-50 p-4 text-center text-sm text-slate-500"
    >
      {{ t('credit_score.history.loading') }}
    </div>

    <div
      v-else-if="entries.length === 0"
      class="rounded-md bg-slate-50 p-4 text-center text-sm text-slate-500"
    >
      {{ t('credit_score.history.empty') }}
    </div>

    <div
      v-else-if="entries.length === 1"
      class="rounded-md bg-emerald-50 p-4 text-center text-sm text-emerald-800 ring-1 ring-emerald-200"
    >
      {{ t('credit_score.history.first_calc') }}
    </div>

    <VizLineChart
      v-else
      :series="series"
      :title="t('credit_score.history.chart_title')"
      :aria-label="t('credit_score.history.chart_aria')"
      :long-description="longDescription"
      size="md"
    />
  </section>
</template>
