<!-- F40 T023 — VizLineChart : chart.js line lazy-loaded. -->
<script setup lang="ts">
import { computed } from 'vue'
import VizChartCanvas from './internal/VizChartCanvas.vue'
import VizSourcePin from './VizSourcePin.vue'
import VizLoadingState from './VizLoadingState.vue'
import VizEmptyState from './VizEmptyState.vue'
import { useChartTheme } from '~/composables/useChartTheme'
import { buildLineConfig } from './internal/buildChartConfig'
import type { BaseChartProps, ChartSeries } from '~/types/viz/chart'

interface Props extends BaseChartProps {
  series: ChartSeries[]
}
const props = withDefaults(defineProps<Props>(), {
  loading: false,
  empty: false,
  size: 'md',
})

const theme = useChartTheme()
const config = computed(() => buildLineConfig(props.series, theme.value, false))
const ariaLabel = computed(() => props.ariaLabel ?? props.title ?? 'Graphique linéaire')
const longDesc = computed(() => props.longDescription ?? buildAutoDescription())

function buildAutoDescription(): string {
  const labels = props.series.map((s) => s.label).join(', ')
  return `Graphique linéaire avec ${props.series.length} série(s) : ${labels}.`
}
const heightForSize = computed(() => ({ sm: '10rem', md: '16rem', lg: '22rem' })[props.size!])
</script>

<template>
  <figure class="viz-chart">
    <figcaption v-if="props.title" class="viz-chart__title">
      {{ props.title }}
      <VizSourcePin v-if="props.source_id" :source_id="props.source_id" />
    </figcaption>
    <ClientOnly>
      <VizLoadingState v-if="props.loading" :height="heightForSize" />
      <VizEmptyState v-else-if="props.empty" :height="heightForSize" />
      <VizChartCanvas
        v-else
        :config="config"
        :aria-label="ariaLabel"
        :long-description="longDesc"
        :height="heightForSize"
      />
      <template #fallback>
        <VizLoadingState :height="heightForSize" />
      </template>
    </ClientOnly>
    <p v-if="props.caption" class="viz-chart__caption">{{ props.caption }}</p>
  </figure>
</template>

<style scoped>
.viz-chart { margin: 0; }
.viz-chart__title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-neutral-900, #171717);
}
.viz-chart__caption {
  margin: 0.5rem 0 0;
  font-size: 0.8rem;
  color: var(--color-neutral-600, #525252);
}
</style>
