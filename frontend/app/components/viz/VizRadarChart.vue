<!-- F40 T027 — VizRadarChart : 6 axes max recommandés (warning au-delà). -->
<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import VizChartCanvas from './internal/VizChartCanvas.vue'
import VizSourcePin from './VizSourcePin.vue'
import VizLoadingState from './VizLoadingState.vue'
import VizEmptyState from './VizEmptyState.vue'
import { useChartTheme } from '~/composables/useChartTheme'
import { buildRadarConfig } from './internal/buildChartConfig'
import type { BaseChartProps, RadarSeries } from '~/types/viz/chart'

interface Props extends BaseChartProps {
  series: RadarSeries
}
const props = withDefaults(defineProps<Props>(), { loading: false, empty: false, size: 'md' })
const theme = useChartTheme()
const heightForSize = computed(() => ({ sm: '12rem', md: '18rem', lg: '24rem' })[props.size!])

const cappedSeries = computed<RadarSeries>(() => {
  const max = 6
  const axes = props.series.axes.slice(0, max)
  return {
    axes,
    datasets: props.series.datasets.map((d) => ({ label: d.label, data: d.data.slice(0, max) })),
  }
})

watchEffect(() => {
  if (props.series.axes.length > 6) {
    // eslint-disable-next-line no-console
    console.warn('[VizRadarChart] >6 axes — tronqué à 6 (lisibilité a11y).')
  }
})

const config = computed(() => buildRadarConfig(cappedSeries.value, theme.value))
const ariaLabel = computed(() => props.ariaLabel ?? props.title ?? 'Graphique radar')
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
      <VizChartCanvas v-else :config="config" :aria-label="ariaLabel" :long-description="props.longDescription ?? ''" :height="heightForSize" />
      <template #fallback><VizLoadingState :height="heightForSize" /></template>
    </ClientOnly>
    <p v-if="props.caption" class="viz-chart__caption">{{ props.caption }}</p>
  </figure>
</template>

<style scoped>
.viz-chart { margin:0; }
.viz-chart__title { display:flex; align-items:center; gap:.4rem; margin:0 0 .5rem; font-size:.95rem; font-weight:600; }
.viz-chart__caption { margin:.5rem 0 0; font-size:.8rem; color: var(--color-neutral-600,#525252); }
</style>
