<!-- F40 T043 — Showcase dev-only de la viz library. -->
<script setup lang="ts">
import { ref } from 'vue'
import VizKPICard from '~/components/viz/VizKPICard.vue'
import VizSourcePin from '~/components/viz/VizSourcePin.vue'
import VizLineChart from '~/components/viz/VizLineChart.vue'
import VizAreaChart from '~/components/viz/VizAreaChart.vue'
import VizBarChart from '~/components/viz/VizBarChart.vue'
import VizStackedBarChart from '~/components/viz/VizStackedBarChart.vue'
import VizRadarChart from '~/components/viz/VizRadarChart.vue'
import VizGaugeChart from '~/components/viz/VizGaugeChart.vue'
import VizPieChart from '~/components/viz/VizPieChart.vue'
import VizDonutChart from '~/components/viz/VizDonutChart.vue'
import VizMermaidRenderer from '~/components/viz/VizMermaidRenderer.vue'
import VizDataTable from '~/components/viz/VizDataTable.vue'
import VizLeafletMap from '~/components/viz/VizLeafletMap.vue'
import VizLoadingState from '~/components/viz/VizLoadingState.vue'
import VizEmptyState from '~/components/viz/VizEmptyState.vue'
import {
  KPI_SAMPLES,
  LINE_SERIES,
  BAR_SERIES,
  STACKED_SERIES,
  RADAR_ESG,
  PIE_SAMPLE,
  MERMAID_VALID,
  MERMAID_INVALID,
  TABLE_COLUMNS,
  MAP_PINS_50,
  makeTableRows,
} from '~/utils/__tests__/fixtures/viz'

definePageMeta({ middleware: ['dev-only'] })

const loading = ref(false)
const empty = ref(false)
const paginate = ref(false)

const tableShortRows = makeTableRows(12)
const tableLongRows = makeTableRows(1000)
</script>

<template>
  <main class="showcase">
    <header class="showcase__head">
      <h1>Visualization Library — F40</h1>
      <div class="showcase__toggles">
        <label><input v-model="loading" type="checkbox"> loading</label>
        <label><input v-model="empty" type="checkbox"> empty</label>
        <label><input v-model="paginate" type="checkbox"> table paginée</label>
      </div>
    </header>

    <section>
      <h2>VizSourcePin (US5)</h2>
      <p>Pin universel : <VizSourcePin source_id="src_demo" /></p>
    </section>

    <section>
      <h2>VizKPICard (US1)</h2>
      <div class="grid grid-3">
        <VizKPICard
          v-for="(k, i) in KPI_SAMPLES"
          :key="i"
          v-bind="k"
          :loading="loading"
          :empty="empty"
        />
      </div>
    </section>

    <section>
      <h2>VizLineChart / VizAreaChart (US2)</h2>
      <div class="grid grid-2">
        <VizLineChart title="Score E mensuel" :series="LINE_SERIES" :loading="loading" :empty="empty" source_id="src_demo" />
        <VizAreaChart title="Score E mensuel (aires)" :series="LINE_SERIES" :loading="loading" :empty="empty" />
      </div>
    </section>

    <section>
      <h2>VizBarChart / VizStackedBarChart (US2)</h2>
      <div class="grid grid-2">
        <VizBarChart title="Pilier ESG" :series="BAR_SERIES" :loading="loading" :empty="empty" />
        <VizStackedBarChart title="Empilées trim." :series="STACKED_SERIES" :loading="loading" :empty="empty" />
      </div>
    </section>

    <section>
      <h2>VizRadarChart / VizGaugeChart (US2/US6)</h2>
      <div class="grid grid-2">
        <VizRadarChart title="Radar E/S/G" :series="RADAR_ESG" :loading="loading" :empty="empty" />
        <VizGaugeChart title="Score global" :value="68" :loading="loading" :empty="empty" />
      </div>
    </section>

    <section>
      <h2>VizPieChart / VizDonutChart (US2)</h2>
      <div class="grid grid-2">
        <VizPieChart title="Mix énergétique" :series="PIE_SAMPLE" :loading="loading" :empty="empty" />
        <VizDonutChart title="Donut mix" :series="PIE_SAMPLE" :loading="loading" :empty="empty" />
      </div>
    </section>

    <section>
      <h2>VizMermaidRenderer (US3)</h2>
      <div class="grid grid-2">
        <VizMermaidRenderer title="Diagramme valide" :payload="MERMAID_VALID" />
        <VizMermaidRenderer title="Diagramme invalide (fallback)" :payload="MERMAID_INVALID" />
      </div>
    </section>

    <section>
      <h2>VizDataTable (US4) — 12 lignes</h2>
      <VizDataTable :rows="tableShortRows" :columns="TABLE_COLUMNS" />
    </section>

    <section>
      <h2>VizDataTable (US4) — 1000 lignes</h2>
      <VizDataTable
        :rows="tableLongRows"
        :columns="TABLE_COLUMNS"
        :paginate="paginate ? { pageSize: 25 } : undefined"
      />
    </section>

    <section>
      <h2>VizLeafletMap (US7)</h2>
      <VizLeafletMap title="50 pins Afrique de l'Ouest" :pins="MAP_PINS_50" />
    </section>

    <section>
      <h2>États génériques</h2>
      <div class="grid grid-2">
        <VizLoadingState height="6rem" />
        <VizEmptyState message="Pas encore de données pour cette période." />
      </div>
    </section>
  </main>
</template>

<style scoped>
.showcase { padding: 1.5rem; max-width: 80rem; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }
.showcase__head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.showcase__toggles { display: flex; gap: 1rem; font-size: .85rem; }
section { display: flex; flex-direction: column; gap: .5rem; }
h2 { margin: 0; font-size: 1rem; color: var(--color-neutral-700, #404040); }
.grid { display: grid; gap: 1rem; }
.grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
@media (max-width: 720px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }
</style>
