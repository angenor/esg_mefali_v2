<!-- F40 T025 — VizBarChart. -->
<script setup lang="ts">
import { computed } from 'vue'
import VizChartCanvas from './internal/VizChartCanvas.vue'
import VizSourcePin from './VizSourcePin.vue'
import VizLoadingState from './VizLoadingState.vue'
import VizEmptyState from './VizEmptyState.vue'
import { useChartTheme } from '~/composables/useChartTheme'
import { buildBarConfig } from './internal/buildChartConfig'
import type { BaseChartProps, CategorySeries } from '~/types/viz/chart'

interface Props extends BaseChartProps {
  series: CategorySeries
}
const props = withDefaults(defineProps<Props>(), { loading: false, empty: false, size: 'md' })
const theme = useChartTheme()
const config = computed(() => buildBarConfig(props.series, theme.value, false))
const ariaLabel = computed(() => props.ariaLabel ?? props.title ?? 'Graphique en barres')
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
