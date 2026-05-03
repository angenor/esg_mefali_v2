<!-- F40 T039 — VizGaugeChart : score 0-100, arc 270°, zones colorées + doublure. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import VizSourcePin from './VizSourcePin.vue'
import VizLoadingState from './VizLoadingState.vue'
import VizEmptyState from './VizEmptyState.vue'
import { useChartTheme } from '~/composables/useChartTheme'
import type { BaseChartProps } from '~/types/viz/chart'

interface Props extends BaseChartProps {
  value: number
  min?: number
  max?: number
}
const props = withDefaults(defineProps<Props>(), {
  min: 0,
  max: 100,
  loading: false,
  empty: false,
  size: 'md',
})

const theme = useChartTheme()
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: { update: () => void; destroy: () => void } | null = null

const clamped = computed<number>(() => Math.max(props.min, Math.min(props.max, props.value)))

// Seuils alignés sur l'independent test US6 (T040) : 12→red, 68→orange, 90→green.
const zone = computed<'red' | 'orange' | 'green'>(() => {
  if (clamped.value <= 33) return 'red'
  if (clamped.value <= 69) return 'orange'
  return 'green'
})

const zoneIcon = computed(() => ({ red: '✕', orange: '!', green: '✓' })[zone.value])

const heightForSize = computed(() => ({ sm: '8rem', md: '12rem', lg: '16rem' })[props.size!])

async function build(): Promise<void> {
  if (!canvas.value) return
  const mod = await import('chart.js/auto')
  const Chart = mod.default
  const remaining = props.max - clamped.value
  const colors = {
    red: ['#ef4444', '#fee2e2'],
    orange: ['#f59e0b', '#fef3c7'],
    green: ['#16a34a', '#dcfce7'],
  }[zone.value]
  Chart.defaults.animation = theme.value.animations.reducedMotion ? false : { duration: theme.value.animations.duration }
  chart = new Chart(canvas.value, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [clamped.value - props.min, remaining],
        backgroundColor: colors,
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      circumference: 270,
      rotation: -135,
      cutout: '70%',
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    } as never,
  }) as never
}

onMounted(() => { void build() })
watch([clamped, theme], () => {
  if (chart) { chart.destroy(); void build() }
})
onBeforeUnmount(() => { if (chart) chart.destroy() })

const ariaLabel = computed(() => props.ariaLabel ?? `Jauge : ${clamped.value} sur ${props.max} (${zone.value})`)
</script>

<template>
  <figure class="viz-gauge">
    <figcaption v-if="props.title" class="viz-gauge__title">
      {{ props.title }}
      <VizSourcePin v-if="props.source_id" :source_id="props.source_id" />
    </figcaption>
    <ClientOnly>
      <VizLoadingState v-if="props.loading" :height="heightForSize" />
      <VizEmptyState v-else-if="props.empty" :height="heightForSize" />
      <div
        v-else
        class="viz-gauge__inner"
        :style="{ height: heightForSize }"
        role="img"
        :aria-label="ariaLabel"
      >
        <canvas ref="canvas" />
        <div class="viz-gauge__center" :data-zone="zone">
          <span class="viz-gauge__icon" aria-hidden="true">{{ zoneIcon }}</span>
          <span class="viz-gauge__value">{{ clamped }}</span>
          <span class="viz-gauge__suffix">/ {{ props.max }}</span>
        </div>
      </div>
      <template #fallback>
        <VizLoadingState :height="heightForSize" />
      </template>
    </ClientOnly>
  </figure>
</template>

<style scoped>
.viz-gauge { margin: 0; }
.viz-gauge__title { display:flex; align-items:center; gap:.4rem; margin:0 0 .5rem; font-size:.95rem; font-weight:600; }
.viz-gauge__inner { position: relative; width: 100%; }
.viz-gauge__inner canvas { width: 100% !important; height: 100% !important; }
.viz-gauge__center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  pointer-events: none;
}
.viz-gauge__center[data-zone="red"] { color: var(--color-danger-700, #b91c1c); }
.viz-gauge__center[data-zone="orange"] { color: var(--color-warning-700, #b45309); }
.viz-gauge__center[data-zone="green"] { color: var(--color-success-700, #15803d); }
.viz-gauge__icon { font-size: 1.25rem; line-height: 1; }
.viz-gauge__value { font-size: 2rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.viz-gauge__suffix { font-size: .8rem; color: var(--color-neutral-500, #737373); }
</style>
